from vnpy.trader.gateway.okexfGateway.okexfGateway import OkexfGateway, OkexfRestApi
from vnpy.api.rest.priority import PriorityRestClient
from vnpy.trader.vtConstant import VN_SEPARATOR

class OkexfpRestApi(PriorityRestClient, OkexfRestApi):
    pass


class OkexfpGateway(OkexfGateway):
    def __init__(self, eventEngine, gatewayName=''):
        """Constructor"""
        super(OkexfpGateway, self).__init__(eventEngine, gatewayName)
        self._priority = 0
        self.restApi = OkexfpRestApi(self)

    @property
    def priority(self):
        return self._priority

    def set_priority(self, priority):
        self._priority = priority

    def sendOrder(self, orderReq):
        self.restApi.set_priority(self._priority)
        super(OkexfpGateway, self).sendOrder(orderReq)


class PrioritySetter(object):
    def __init__(self, gateways, priorty):
        self._old_priorty = {}
        self._gateways = gateways
        self._priority = priorty

    def __enter__(self):
        for gateway in self._gateways:
            self._old_priorty[gateway.gatewayName] = gateway.priority
            gateway.set_priority(self._priority)

    def __exit__(self, type, value, traceback):
        for gateway in self._gateways:
            gateway.set_priority(self._old_priorty[gateway.gatewayName])


class PriorityHelper(object):
    def __init__(self, strategy):
        self._strategy = strategy
        self._ctaEngine = strategy.ctaEngine
        self._mainEngine = self._ctaEngine.mainEngine
        self._gateways = None

    @property
    def gateways(self):
        if self._gateways is None:
            self._gateways = self._find_gateways()
        return self._gateways

    def _find_gateways(self):
        gateways = []
        for symbol in self._strategy.symbolList:
            gatewayname = VN_SEPARATOR.join(symbol.split(VN_SEPARATOR)[:-1])
        if gatewayname.upper().startswith("OKEXFP_"):
            gateway = self._ctaEngine.getGateway(gatewayname)
            if gateway:
                gateways.append(gateway)
        return gateways 

    def with_priority(self, priority):
        return PrioritySetter(self.gateways, priority)

    def set_priority(self, priority):
        for gateway in self.gateways:
            gateway.set_priority(priority)
