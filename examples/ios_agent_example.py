#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
iOS Agent 使用示例
演示如何像使用 Android Agent 一样使用 iOS Agent
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from page_eyes.agent import IOSAgent


async def example_basic():
    """基础示例：使用 iOS Agent 执行简单任务"""
    print("=" * 60)
    print("示例 1: iOS 打开URL，搜索，滑动测试")
    print("=" * 60)
    
    # WDA地址会自动从 .env 文件的 IOS_WDA_URL 读取
    # 如果需要指定地址，可以传入 wda_url 参数
    ios_agent = await IOSAgent.create(debug=True)
    
    prompt = """ 
        - 打开 url "https://yobang.tencentmusic.com/chart/uni-chart/rankList/"
        - 检查页面是否有 "close" 按钮，如果有则点击 "close" 按钮
        - 找到并打开搜索框
        - 搜索 “蔡徐坤”
        - 等待3秒，直到出现相关歌曲
        - 向上滑动，直到出现"没有意外"
        """
    
    print(f"\n执行指令: {prompt}\n")
    result = await ios_agent.run(prompt)
    
    print(f"\n执行结果: {result}")



async def example_settings_automation():
    print("\n" + "=" * 60)
    print("示例 2: iOS 回到桌面、打开应用测试")
    print("=" * 60)
    
    ios_agent = await IOSAgent.create(debug=False)
    
    prompt = """
    1. 回到桌面
    2. 打开设置应用
    3. 进入通用设置
    4. 进入关于本机
    5. 查看iOS版本信息
    """
    
    print(f"\n执行多步骤任务:\n{prompt}\n")
    result = await ios_agent.run(prompt)
    
    print(f"\n任务完成!")
    print(f"执行步骤数: {len(ios_agent.deps.context.steps)}")
    
    for step_num, step_info in ios_agent.deps.context.steps.items():
        print(f"\n步骤 {step_num}:")
        print(f"  动作: {step_info.action}")
        print(f"  描述: {step_info.description}")
        print(f"  成功: {step_info.is_success}")


async def example_custom_app():
    """示例 3: 操作自定义应用"""
    print("\n" + "=" * 60)
    print("示例 3: 打开URL、回退测试")
    print("=" * 60)
    
    ios_agent = await IOSAgent.create()
    
    prompt = """
    1. 打开url"apple.com"
    2. 再打开url"baidu.com"
    3. 向上滑动两次，再往下滑动一次
    4. 返回上一页
    """
    
    result = await ios_agent.run(prompt)
    


async def example_with_assertion():
    """示例 4: 带断言的测试"""
    print("\n" + "=" * 60)
    print("示例 4: 打开URL，搜索测试")
    print("=" * 60)
    
    ios_agent = await IOSAgent.create()
    
    prompt = """
    1.打开“baidu.com”
    2.搜索 “2026blast春决
    """
    
    print(f"\n执行测试:\n{prompt}\n")
    result = await ios_agent.run(prompt)


async def compare_android_ios():
    """示例 5: 对比 Android 和 iOS 的使用方式"""
    print("\n" + "=" * 60)
    print("示例 5: Android vs iOS Agent 对比（AI生成）")
    print("=" * 60)
    
    print("\n【Android Agent 使用方式】")
    print("""
from page_eyes.agent import MobileAgent

# 创建 Android Agent
android_agent = await MobileAgent.create(
    serial="127.0.0.1:5555",  # 设备序列号
    platform=Platform.QY,
    debug=True
)

# 执行任务
result = await android_agent.run("打开设置，查看系统版本")
    """)
    
    print("\n【iOS Agent 使用方式】")
    print("""
from page_eyes.agent import IOSAgent

# 创建 iOS Agent
ios_agent = await IOSAgent.create(
    wda_url="http://localhost:8100",  # WebDriverAgent 地址
    platform=Platform.QY,
    debug=True
)

# 执行任务（语法完全一致！）
result = await ios_agent.run("打开设置，查看系统版本")
    """)
    
    print("\n两者的使用方式几乎完全一致！")
    print("唯一的区别是:")
    print("  Android: 需要 serial (设备序列号)")
    print("  iOS:     需要 wda_url (WebDriverAgent 地址)")


def main():
    """主函数 - 交互式选择示例"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    iOS Agent 使用示例                             ║
║                                                                  ║
║  本示例展示如何像使用 Android Agent 一样使用 iOS Agent            ║
╚══════════════════════════════════════════════════════════════════╝

请选择要运行的示例:

1. 基础使用示例
2. 设置自动化示例  
3. 操作自定义应用示例
4. 带断言的测试示例
5. Android vs iOS 对比说明
6. 运行所有示例

0. 退出
    """)
    
    choice = input("\n请输入选项 (0-6): ").strip()
    
    examples = {
        "1": example_basic,
        "2": example_settings_automation,
        "3": example_custom_app,
        "4": example_with_assertion,
        "5": compare_android_ios,
    }
    
    if choice == "0":
        print("退出")
        return
    elif choice == "6":
        print("\n运行所有示例...\n")
        for example in examples.values():
            try:
                asyncio.run(example())
            except Exception as e:
                print(f"示例执行出错: {e}")
            print("\n" + "-" * 60 + "\n")
    elif choice in examples:
        try:
            asyncio.run(examples[choice]())
        except Exception as e:
            print(f"执行出错: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("无效选项")


if __name__ == "__main__":
    main()