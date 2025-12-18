from django.http import HttpResponse


class SimpleCorsMiddleware:
    """
    Minimal CORS middleware to allow cross-origin calls in dev without extra dependency.
    Allows all origins; for production, tighten as needed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = request.headers.get(
            "Access-Control-Request-Headers", "Content-Type, Authorization"
        )
        response["Access-Control-Allow-Credentials"] = "true"
        return response
