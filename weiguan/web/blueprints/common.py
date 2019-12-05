import traceback
from functools import wraps

from sanic import response
from sanic.exceptions import SanicException
from pymysql.err import IntegrityError

from ...container import Container
from ...entities import PostSchema, UserSchema, PostStatSchema, UserStatSchema
from ...services import UsecaseException, UnauthenticatedException, \
    UnauthorizedException, NotFoundException


def response_json(code='ok', message='', status=200, **data):
    return response.json({'code': code.value, 'message': message, 'data': data},
                         status)


def handle_exception(request, e):
    traceback.print_exc()

    status = 200
    code = 'fail'
    message = repr(e)
    if isinstance(e, SanicException):
        if e.status_code is not None:
            status = e.status_code
    elif isinstance(e, UnauthenticatedException):
        status = 401
        code = 'unauthenticated'
        message = e.message
    elif isinstance(e, UnauthorizedException):
        status = 403
        code = 'unauthorized'
        message = e.message
    elif isinstance(e, NotFoundException):
        status = 404
        code = 'not_found'
        message = e.message
    elif isinstance(e, UsecaseException):
        message = e.message

    data = {}
    config = Container().config
    if config['DEBUG']:
        data['exception'] = traceback.format_exc()

    return response_json(code, message, status, **data)


def authenticated():
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            if request['session'].get('user') is None:
                raise UnauthenticatedException('未认证')

            return await f(request, *args, **kwargs)

        return decorated_function

    return decorator


async def dump_user_info(user, user_id=None):
    if user is None:
        return None

    file_service = Container().file_service
    user['avatar'] = await file_service.file_info(user['avatar_id'])

    user = UserSchema().dump(user)

    stat_service = Container().stat_service
    stat = await stat_service.user_stat_info_by_user_id(user['id'])
    if stat is not None:
        stat = UserStatSchema().dump(stat)
    user['stat'] = stat

    if user_id is not None:
        user_service = Container().user_service
        user['isFollowing'] = (await user_service.is_following_users(
            user_id, [user['id']]))[0]

    return user


async def dump_user_infos(users, user_id=None):
    if not users:
        return []

    file_service = Container().file_service
    files = await file_service.file_infos([v['avatar_id'] for v in users])
    for user, file in zip(users, files):
        user['avatar'] = file

    users = [UserSchema().dump(v) for v in users]

    stat_service = Container().stat_service
    stats = await stat_service.user_stat_infos_by_user_ids(
        [v['id'] for v in users])
    for user, stat in zip(users, stats):
        if stat is not None:
            stat = UserStatSchema().dump(stat)
        user['stat'] = stat

    if user_id is not None:
        user_service = Container().user_service
        is_followginss = await user_service.is_following_users(
            user_id, [v['id'] for v in users])
        for user, is_followgins in zip(users, is_followginss):
            user['isFollowing'] = is_followgins

    return users


async def dump_post_info(post, user_id=None):
    if post is None:
        return None

    user_service = Container().user_service
    user = await user_service.info(post['user_id'])

    file_service = Container().file_service
    user['avatar'] = await file_service.file_info(user['avatar_id'])

    post['user'] = user

    post['image_ids'] = post['image_ids'] or []
    post['images'] = await file_service.file_infos(post['image_ids'])

    post['video'] = await file_service.file_info(post['video_id'])

    post = PostSchema().dump(post)

    stat_service = Container().stat_service
    stat = await stat_service.post_stat_info_by_post_id(post['id'])
    if stat is not None:
        stat = PostStatSchema().dump(stat)
    post['stat'] = stat

    if user_id is not None:
        post_service = Container().post_service
        post['isLiked'] = (await post_service.is_liked_posts(
            user_id, [post['id']]))[0]

    return post


async def dump_post_infos(posts, user_id=None):
    if not posts:
        return []

    user_service = Container().user_service
    users = await user_service.infos([v['user_id'] for v in posts])

    file_service = Container().file_service
    files = await file_service.file_infos([v['avatar_id'] for v in users])
    for user, file in zip(users, files):
        user['avatar'] = file

    for post, user in zip(posts, users):
        post['user'] = user

    for post in posts:
        post['image_ids'] = post['image_ids'] or []
    images = await file_service.file_infos(
        [image_id for post in posts for image_id in post['image_ids']])
    start = 0
    for post in posts:
        length = len(post['image_ids'])
        post['images'] = images[start:start+length]
        start += length

    files = await file_service.file_infos([v['video_id'] for v in posts])
    for post, file in zip(posts, files):
        post['video'] = file

    posts = [PostSchema().dump(v) for v in posts]

    stat_service = Container().stat_service
    stats = await stat_service.post_stat_infos_by_post_ids(
        [v['id'] for v in posts])
    for post, stat in zip(posts, stats):
        if stat is not None:
            stat = PostStatSchema().dump(stat)
        post['stat'] = stat

    if user_id is not None:
        post_service = Container().post_service
        is_likeds = await post_service.is_liked_posts(
            user_id, [v['id'] for v in posts])
        for post, is_liked in zip(posts, is_likeds):
            post['isLiked'] = is_liked

    return posts
