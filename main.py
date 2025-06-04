from adbutils import AdbClient, AdbDevice
from dotenv import load_dotenv
from pydantic_ai.tools import RunContext

from ieyes_agent.agent import MobileAgent
from ieyes_agent.deps import AgentDeps
from ieyes_agent.tools import AndroidAgentTool

load_dotenv()


def parser_screen():
    device: AdbDevice = AdbClient().device_list()[0]
    deps = AgentDeps({'device_name': 'test', 'screen_resolution': '1080x2400'}, device)
    android_tool = AndroidAgentTool()
    data = android_tool.get_device_screen_elements(RunContext(deps, '', '', ''))
    print(data)


def main():
    client = AdbClient()
    device: AdbDevice = client.device_list()[0]
    size = device.window_size()
    device_name = device.prop.name
    # print(device_name)

    deps = AgentDeps({'device_name': device_name, 'screen_resolution': f'{size.width}x{size.height}'}, device)
    ui_agent = MobileAgent('openai:deepseek/deepseek-chat', deps)
    # ui_agent.run('1.点击 Find icon\n2.在搜索输入框中输入"小美满"\n3.点击"小美满> "\n4.点击"查看更多成绩"')
    # ui_agent.run('1.点击第一个推荐按钮\n2.点击单曲购买\n3.点击"超会连续包月"\n4.点击"立即购买"')
    ui_agent.run('1.点击搜索icon\n2.在搜索输入框中输入"小美满"')
    # ui_agent.run('点击日榜')


if __name__ == "__main__":
    main()
    # parser_screen()
