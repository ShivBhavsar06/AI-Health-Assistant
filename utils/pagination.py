from flask import request


def paginate_query(query, per_page=10):
    try:
        page = int(request.args.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    return query.paginate(page=page, per_page=per_page, error_out=False)
