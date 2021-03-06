# Django imports
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Prefetch, OuterRef, Subquery, Q, Count

# App imports
from imageboard.models import Board, Thread
from imageboard.views.parts import set_session_data_as_cookie
from imageboard.views.parts import prefetch_posts_related_data


def start_page(request):
    # Create response object
    response = HttpResponse()

    # Send some user session data as cookies
    set_session_data_as_cookie(request, response, 'user_threads')
    set_session_data_as_cookie(request, response, 'user_posts')
    set_session_data_as_cookie(request, response, 'user_thread_replies')

    # Select some most recently updated threads
    updated_threads_queryset = Thread.objects\
        .filter(board=OuterRef('board'), is_deleted=False)\
        .order_by('-is_sticky', '-updated_at')\
        .values_list('id', flat=True)[:5]

    # Prefetch threads
    threads_prefetch = Prefetch(
        'threads',
        queryset=Thread.objects
                       .filter(Q(id__in=Subquery(updated_threads_queryset)))
                       .order_by('-is_sticky', '-updated_at')
                       .annotate(posts_count=Count('posts')),
        to_attr='updated_threads'
    )

    # Prefetch OP posts
    op_prefetch_args = prefetch_posts_related_data('updated_threads__op')

    # Get boards with threads and OP posts
    boards = Board.objects\
        .order_by('hid')\
        .filter(is_deleted=False, is_hidden=False)\
        .prefetch_related(threads_prefetch)\
        .prefetch_related(*op_prefetch_args)

    rendered_template = render_to_string(
        'imageboard/start_page.html',
        {
            'boards': boards,
        },
        request
    )

    response.write(rendered_template)
    return response
