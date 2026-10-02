import asyncio
import json
from pathlib import Path
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_skill_generator_stages_and_tests_code(tmp_path:Path):
    payload=json.dumps({
        "executor_py": "def execute(payload):\n    return {'success': True, 'output': {'value': payload.get('value')}}",
        "test_py": "from executor import execute\n\ndef test_execute():\n    assert execute({'value': 3})['output']['value'] == 3",
        "capabilities": ["demo.generated"],
        "permissions": [],
    })
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider(payload))
        try:
            result=await rt.skill_generator.generate("demo.generated","Echo a value")
            assert result["ready_for_install"] is True
            assert Path(result["path"]).exists()
        finally:
            await rt.close()
    asyncio.run(scenario())
