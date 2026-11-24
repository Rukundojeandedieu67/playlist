from django.db import connection, transaction


class DatabaseClaimsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            with transaction.atomic():
                return self.get_response(request)
        return self.get_response(request)


def set_database_claims(user_id):
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('request.jwt.claim.sub', %s, true), "
            "set_config('request.jwt.claim.role', %s, true)",
            [user_id, "authenticated"],
        )
