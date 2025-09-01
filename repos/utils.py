from qm.models import Analytic

def re_escape(s):
    return s.encode('unicode_escape').decode('utf-8')

def nb_analytics_imported(repo):
    """
    Count number of analytics in a given repo
    :param repo: object (Repo)
    :return: number of imported analytics (int)
    """
    return Analytic.objects.filter(repo=repo).exclude(status='ARCH').count()

def is_imported(analytic_name, repo):
    """
    Check if an analytic is imported in a given repo
    :param analytic_name: string representing the analytic name to search for
    :param repo: object (Repo)
    :return: boolean indicating whether the analytic is imported
    """
    analytic = Analytic.objects.filter(repo=repo, name=analytic_name).exclude(status='ARCH')
    return analytic.exists()
