from jarvis.models import ModelRegistry,ModelRouter,MockModelProvider


class CloudMock(MockModelProvider):
    provider_id="cloud"
    default_model="cloud-model"


def test_router_prefers_local_for_private_and_cloud_when_allowed():
    reg=ModelRegistry()
    local=MockModelProvider()
    local.provider_id="local"
    local.default_model="local-model"
    cloud=CloudMock()
    reg.register(local,{"local":True,"paid":False,"capabilities":["general"]})
    reg.register(cloud,{"local":False,"paid":False,"capabilities":["general","coding"]})
    router=ModelRouter("local","local-model",reg)
    assert router.route(capability="coding",privacy="local").provider=="local"
    assert router.route(capability="coding",privacy="cloud",budget="free").provider=="cloud"
