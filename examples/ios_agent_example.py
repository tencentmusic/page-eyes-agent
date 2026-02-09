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
    print("=" * 60)
    
    ios_agent = await IOSAgent.create(
        #改为自己的WDA运行地址
        wda_url="http://10.91.215.96:8100",
        debug=True
    )
    
    prompt = "打开设置应用，打开通用tab，打开关于手机，查看iOS版本"
    
    print(f"\n执行指令: {prompt}\n")
    result = await ios_agent.run(prompt)
    
    print(f"\n执行结果: {result}")



async def example_settings_automation():
    print("\n" + "=" * 60)
    print("示例 2: iOS 设置自动化")
    print("=" * 60)
    
    ios_agent = await IOSAgent.create(
        wda_url="http://10.91.215.96:8100",
        debug=False
    )
    
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
    print("示例 3: 操作自定义应用")
    print("=" * 60)
    
    ios_agent = await IOSAgent.create()
    
    prompt = """
    1. 打开Safari浏览器
    2. 在地址栏输入"www.apple.com"
    3. 等待页面加载完成
    4. 截图保存
    """
    
    print(f"\n执行指令:\n{prompt}\n")
    result = await ios_agent.run(prompt)
    
    print(f"\n执行完成: {result.data.is_success}")


async def example_with_assertion():
    """示例 4: 带断言的测试"""
    print("\n" + "=" * 60)
    print("示例 4: 带断言的自动化测试")
    print("=" * 60)
    
    ios_agent = await IOSAgent.create()
    
    prompt = """
    1. 打开设置
    2. 验证页面包含"通用"和"隐私"
    3. 点击通用
    4. 验证页面包含"关于本机"
    """
    
    print(f"\n执行测试:\n{prompt}\n")
    result = await ios_agent.run(prompt)
    
    if result.data.is_success:
        print("✅ 测试通过")
    else:
        print("❌ 测试失败")


async def compare_android_ios():
    """示例 5: 对比 Android 和 iOS 的使用方式"""
    print("\n" + "=" * 60)
    print("示例 5: Android vs iOS Agent 对比")
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