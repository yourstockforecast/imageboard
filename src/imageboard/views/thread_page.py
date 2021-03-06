# Django imports
from django.template.loader import render_to_string
from django.db.models import Prefetch, Count
from django.http import HttpResponse

# App imports
from imageboard.models import Thread, Post
from imageboard.forms import PostingForm
from imageboard.views import parts
from imageboard.views.parts import CacheInterface, prefetch_posts_related_data


def thread_page(request, board_hid, thread_hid):
    # Create response object
    response = HttpResponse()

    # Send some user session data as cookies
    parts.set_session_data_as_cookie(request, response, 'user_threads')
    parts.set_session_data_as_cookie(request, response, 'user_posts')
    parts.set_session_data_as_cookie(request, response, 'user_thread_replies')

    # Get boards
    boards = parts.get_boards()

    # Get current board
    board = parts.get_board(board_hid)

    # Thread queryset
    thread = parts.get_thread(board_hid, thread_hid)

    # Create cache interface
    cache_interface = CacheInterface(
        key='thread_page__{board_hid}__{thread_hid}'.format(board_hid=board_hid, thread_hid=thread_hid),
        obj=thread,
        is_admin=request.user.is_authenticated
    )

    # Get cached page if exists and return it
    cached_template = cache_interface.get_cached_template()
    if cached_template:
        response.write(cached_template)
        return response

    posts_queryset = Post.objects.filter(is_deleted=False)

    prefetch_args = prefetch_posts_related_data('posts', posts_queryset=posts_queryset)

    # Prefetch stuff for the thread
    thread = Thread.objects\
        .select_related('board')\
        .prefetch_related(*prefetch_args) \
        .annotate(posts_count=Count('posts')) \
        .get(board__hid=board_hid, hid=thread_hid, is_deleted=False)

    # Add extra data
    thread.other_posts = []
    for post in thread.posts.all():
        if post.is_op:
            thread.op = post
        else:
            thread.other_posts.append(post)

    # Init post creation form
    form = PostingForm(
        initial={
            'form_type': 'new_post',
            'board_id': board.id,
            'thread_id': thread.id,
        },
    )

    # Cache data
    cache_data = cache_interface.make_cache_info(board=board, thread=thread)

    # Render template
    rendered_template = render_to_string(
        'imageboard/thread_page.html',
        {
            'page_type': 'thread_page',
            'form': form,
            'board': board,
            'boards': boards,
            'thread': thread,
            'cache_data': cache_data,
        },
        request
    )

    # Write page to cache
    cache_interface.write_template_to_cache(rendered_template)

    # Return response
    response.write(rendered_template)
    return response
