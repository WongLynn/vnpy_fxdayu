# OkexfpGateway 
`OkexfpGateway`是在有优先级区分的两个进程中进行下单的okex期货Gateway

## 使用方法
1. 使用`OkexfpGateway`代替`OkexfGateway`
2. 使用`vnpy.trader.gateway.okefpGateway.okexfpGateway.CtaTemplate`作为`CtaTemplate`来让策略对象继承之
3. 以上`CtaTemplate` 多暴露了两个接口`set_priority`和`with_priority`来设置gateway当前的优先级，<=0为低优先级，>0为高优先级，默认值为0。以下为使用示例:
    ```python
    from vnpy.trader.gateway.okefpGateway.okexfpGateway import CtaTemplate

    class StrategyA(CtaTemplate):
        def onBar(self):
            self.set_priority(1)
            self.buy(...) # 以高优先级下单，直至下一次修改priority
            self.set_priority(0)
            self.buy(...) # 以低优先级下单，直至下一次修改priority
    ```
    以上等价于:
    ```python
    from vnpy.trader.gateway.okefpGateway.okexfpGateway import CtaTemplate

    class StrategyA(CtaTemplate):
        def onBar(self):
            with self.with_priority(1):
                self.buy(...) # 在with语句内，以高优先级下单
            # priority 恢复为默认值0 
            self.buy(...) # 以低优先级下单
    ```
