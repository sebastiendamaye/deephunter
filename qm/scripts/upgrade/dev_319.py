"""
Dev #319 - Move error related fields, next review date and last time seen fields to AnalyticMeta table
This script populates the AnalyticMeta table from existing analytics
"""

from qm.models import Analytic, AnalyticMeta

def run():
    # Populate the AnalyticMeta table from existing analytics (even archived ones)
    for analytic in Analytic.objects.all():
        # Check if AnalyticMeta already exists for this analytic
        analayticmeta, created = AnalyticMeta.objects.get_or_create(analytic=analytic,
                                    defaults={
                                        'maxhosts_count': analytic.maxhosts_count,
                                        'query_error': analytic.query_error,
                                        'query_error_date': analytic.query_error_date,
                                        'last_time_seen': analytic.last_time_seen,
                                        'next_review_date': analytic.next_review_date
                                    })
        if created:
            print(f" - Created AnalyticMeta for Analytic ID {analytic.id}")
        else:
            print(f" - AnalyticMeta already exists for Analytic ID {analytic.id}")

    print("")
    print("""[i] You should run "./manage.py clean_duplicate_history --auto" after this script to clean up any duplicate historical records.""")
    print("")
