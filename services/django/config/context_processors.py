from django.conf import settings


def analytics_settings(request):
    return {
        "google_analytics_measurement_id": settings.GOOGLE_ANALYTICS_MEASUREMENT_ID,
    }
