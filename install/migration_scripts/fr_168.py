from connectors.models import Connector, ConnectorConf

connector = Connector.objects.get(name='sentinelone')
connector_conf = ConnectorConf(
    connector=connector,
    key = 'QUERY_ERROR_INFO_',
    value='',
    description='Regular expression to filter what should be considered INFO instead of ERROR in query error message'
)
connector_conf.save()

connector = Connector.objects.get(name='microsoftsentinel')
connector_conf = ConnectorConf(
    connector=connector,
    key = 'QUERY_ERROR_INFO_',
    value='',
    description='Regular expression to filter what should be considered INFO instead of ERROR in query error message'
)
connector_conf.save()
