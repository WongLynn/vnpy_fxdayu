# encoding: UTF-8

from __future__ import absolute_import
from vnpy.trader import vtConstant
from .okexfpGateway import OkexfpGateway

gatewayClass = OkexfpGateway
gatewayName = 'OKEXFP'
gatewayDisplayName = 'OKEXFP'
gatewayType = vtConstant.GATEWAYTYPE_BTC
gatewayQryEnabled = True
