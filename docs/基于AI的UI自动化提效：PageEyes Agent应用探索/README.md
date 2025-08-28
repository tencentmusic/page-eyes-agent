# 基于AI的UI自动化提效：PageEyes Agent应用探索

### 一、背景

##### 1.1 业务质量保障之痛

腾讯音乐榜是一个面向C端用户的榜单产品，内嵌在TME音乐app内的H5，如下所示。产品入口包含QQ音乐、酷狗音乐、酷我音乐等，产品形态为腾讯音乐各类榜单及商业化活动。

<img title="腾讯音乐榜" src="https://cdn-y.tencentmusic.com/f0bf1c880caad3cdc4a644fc1267deb7.webp" alt="" style="display: block; margin: 0 auto;" width="510">

因此，对于这种多端多场景的业务测试复杂度，存在以下挑战：

- 业务规模大：腾讯音乐榜以及周边商业化运营项目往往投放多个平台和多个端，比如浪潮大赏和盘点类项目一次上线可能同时发布上百个页面，测试需要覆盖的范围大
- 故障成本高：面向C端用户的榜单及活动，一旦出现页面crash、白屏、报错等，会引发大量客诉、舆情等，不仅会影响榜单公信力，甚至导致资损

##### 1.2 传统UI自动化困局

针对榜单C端H5的核心业务场景，我们先后基于Airtest框架和TestCafe框架构建UI自动化巡检体系。选择这两个框架的考量因素包括：

- Airtest：基于图像识别的跨平台特性，适合H5在不同设备的兼容性测试
- TestCafe：JavaScript原生支持，与前端技术栈契合度高，支持真实浏览器环境测试

然而，实践过程中UI自动化领域的经典问题相继出现......

- 用例维护时长占比
- 误报率问题
- 执行效率
- 投入产出比

对应地，我们也实施过很多优化手段，在稳定性提升上，优化元素定位、智能等待、POM设计模式；在可维护性提升上，用测试数据追求脚本高复用、用低代码降低脚本编写门槛；在执行效率优化上，分布式提升运行时效、报错重试拉起等。

随着业务敏捷迭代，这块自动化的维护出现了成本效率结构失衡问题，我们逐渐意识到，或许不是技术实现的问题，而是测试策略选择的问题。

##### 1.3 PageEyes 页面UI质量巡检

经过对历史线上故障问题点的统计，我们发现大部分问题为样式、布局错乱、页面异常报错、渲染白屏等，针对这类UI样式问题，我们初步做了页面UI质量巡检。

详见 《页面异常检测》xxx文章链接

### 二、PageEyes Agent 介绍

PageEyes Agent 是基于 [Pydantic AI](https://ai.pydantic.dev/#why-use-pydanticai) 框架开发的一个轻量级 UI Agent，
其中元素信息感知能力依靠 [OmniParserV2](https://huggingface.co/microsoft/OmniParser-v2.0) 模型，整个 Agent 的优势在于不依赖视觉语言大模型，
即使小参数的 LLM 也能胜任路径规划能力，同时支持多平台（Web、Android），目前主要包含以下功能：

1. 完全由自然语言指令驱动，无需编写脚本，既可实现自动化测试，UI巡检等任务
2. 跨平台、夸端支持，在 Python 环境中安装 page-eyes 库和配置 OmniParser 服务后即可开始 Web、Android 平台的自动化任务，未来还将继续支持iOS平台
3. 支持多种大模型接入，包括DeepSeek、OpenAI、千问等，默认使用 DeepSeek V3 模型，后续会支持更多大模型接入
4. 可通过自然语言进行断言，并生成详细的执行日志和报告，方便测试人员查看执行过程和结果

##### 2.1 PageEyes Agent 架构

**整体框架**
<img title="" src="https://cdn-y.tencentmusic.com/251563cb2c122f012d772699c1bd93a2.png" alt="" style="display: block; margin: 0 auto;" width="425">

**Agent 执行流程**
<img title="" src="https://cdn-y.tencentmusic.com/1e1e171e6dd06b6808489acd381db735.png" alt="" style="display: block; margin: 0 auto;" width="679">

#### 2.2 信息感知方案的选择

信息感知方案选择上我们分别对比了用得比较多的几种：
<img title="" src="https://cdn-y.tencentmusic.com/ac78855205d75f94dccc3c4083e50f9c.png" alt="" width="666" style="display: block; margin: 0 auto;">

**结论**

🔲 使用视觉语言模型简单、稳定，但API调用费用高昂且响应速度一般，不适用大规模应用  
🔲 Droidrun 成本低、速度快，但对纯icon元素感知能力弱，仅适用于有明确按钮文案或元素名称的Android应用页面  
✅ OmniParser 需额外部署模型，但对机器配置要求不高，元素解析稳定，适用全平台  

#### 2.2 PageEyes Agent 提示词工程示例

<img title="" src="https://cdn-y.tencentmusic.com/b968ab8e68441dcf4307ad8804ed95bb.png" alt="" width="699" style="display: block; margin: 0 auto;">

#### 2.3 PageEyes Agent 稳定性优化的一些策略

- 设计上我们只依赖模型的规划能力和元素解析能力，所以小模型也能胜任
- 截图处理上只截取当前视口范围的内容同时对图片进行了适当压缩，减少非必要元素Token消耗，同时提高处理速度
- 元素解析上我们利用 RAG 技术对截图进行了向量化存储，相同图片的解析结果会被复用提交给大模型，减少重复解析资源和耗时
- 最后是做了一些缓存和监控，减少大量的重复调用，以及能及时优化一些不稳定的任务

### 三、PageEyes Agent应用示例

##### 3.1 腾讯音乐榜-周榜搜索

完成周榜搜索一共只需要3步

step 1:录入任务和交互指令
在PageEyes管理后台录入测试任务，配置页面URL、交互指令、检测类型等。其中，由于是基于agent的交互类巡检，需要提供交互指令：

1. 点击关闭弹窗，没有弹窗则跳过步骤;
2. 点击“查找icon”;
3. 搜索输入框内输入“周深”;
4. 点击第1首歌;

完整配置如下图所示
<img title="腾讯音乐榜" src="https://cdn-y.tencentmusic.com/02861ddef1bd1d3452699c1d6408fb95.webp" alt="" style="display: block; margin: 0 auto;" width="251">

step 2: 执行单次任务查看效果
<img title="腾讯音乐榜" src="https://cdn-y.tencentmusic.com/13ca4e1007c6d8fddedcb1d6376d3192.webp" alt="" style="display: block; margin: 0 auto;" width="654">

step 3: 查看结果报告
执行成功后查看结果报告，报告内还包含了执行过程录像。
<img title="腾讯音乐榜" src="https://cdn-y.tencentmusic.com/17d0c310f0686d15bf6c9cb83146be74.webp" alt="" style="display: block; margin: 0 auto;" width="571">

<img title="" src="https://cdn-y.tencentmusic.com/050132335ac96e8ce7dfe3dd4834a6e3.png" alt="" width="566" style="display: block; margin: 0 auto;">

<img title="" src="https://cdn-y.tencentmusic.com/c23e618af4428528c7f731bfbd42cbd3.gif" alt="" style="display: block; margin: 0 auto;" width="385">

通过回看执行过程，可以看到agent基本遵循了输入的交互指令：找到搜索icon并点击 -> 输入搜索词并回车 -> 选取搜索结果并点击
<img title="腾讯音乐榜" src="https://cdn-y.tencentmusic.com/939d2a2f924edd1e4519a24f3620ff4c.webp" alt="" style="display: block; margin: 0 auto;">

完整版页面截屏录像见:  [点击查看视频](https://cdn-y.tencentmusic.com/uni/commonPic/cos_db21ebf3718f3e7d94669df16cb3656067cf5e66.webm) 

这样，一个搜索demo的任务配置完成，后续会每半小时巡检一次，不通过时将通过告警群推送消息。

### 四、业内GUI-Agent工具试用

##### 4.1 主流GUI Agent工具对比

| 工具名称            | 核心技术           | 适用平台    | 主要优势                                         | 不足                                                 | 开源状态 | 应用场景           |
| --------------- | -------------- | ------- | -------------------------------------------- | -------------------------------------------------- | ---- | -------------- |
| UI-TARS-Desktop | 多模态VLM + 系统2推理 | Web/移动端 | • 复杂任务分解能力强<br> • 多模态理解准确<br>• 支持复杂工作流<br>   | • 需高性能GPU支持<br>• 推理延迟较高<br>• 成本相对较高<br>            | 部分开源 | 复杂业务流程自动化      |
| AppAgent        | 操作历史抽象 + 记忆机制  | 移动端     | • 自动化归纳高效操作模式<br>• 学习能力强<br>• 适应用户习惯<br>     | • 对动态界面适应性待提升<br>• 主要限于Android平台<br>• 需要大量训练数据<br> | 开源   | 移动应用重复操作自动化    |
| AutoGLM         | 渐进式强化学习        | 移动端     | • 自然语言交互门槛低<br>• 持续学习改进<br>• 中文支持较好<br>      | • 仅限手机端任务<br>• 跨应用能力有限<br>• 对复杂逻辑处理较弱<br>          | 开源   | 手机生活类应用日常操作自动化 |
| OmniParser      | 视觉元素解析 + OCR   | 全平台     | • 独立于HTML/视图层级<br>• 跨平台兼容性强<br>• 视觉解析精度高<br> | • 对低质量图像敏感<br>• 处理速度相对较慢<br>                       | 开源   | 跨平台UI元素识别      |

从上述近期较热门的GUI Agent分析来看，未来Agent优化存在的技术演进方向大致可分为以下几类：

- 从单纯“视觉”分析转向“视觉+语言+操作历史”的综合分析
- 模型感知推理能力提升，增强对新页面和新场景的理解与分析
- 轻量化部署，降低GPU依赖，支持边缘设备部署

那么再回到之前讨论的传统UI自动化经典问题，结合PageEyes Agent现有能力，可以看到编写效率极大提高，UI频繁变动带来的元素定位和维护基本转换为指令录入，自动化步骤错误也将经过一层Agent过滤，误报得到控制。

##### 4.2 字节UI-TARS使用体验

UI-Tars desktop，使用Computer Operator模式
体验优点：模型有一定感知和推理能力，见官网 https://github.com/bytedance/UI-TARS-desktop 。如下，我提供的输入指令只包含4步，但在页面没有找到目标歌手的情况下，主动找到搜索框元素进行搜索动作，最后成功输出了准确结果。模型的思考步骤透明化，方便调试修改指令

体验缺点：移动端H5通过operator-adb控制支持选项不多，PC端日常办公提效无法使用

<img title="腾讯音乐榜" src="https://cdn-y.tencentmusic.com/fa10e4ba3b02a3372c62daf5575753db.webp" alt="" width="625" style="display: block; margin: 0 auto;">

### 五、总结

从去年10月份开始的自动化工作流，到今年年初涌现的大批自动化Agent，再到最近火爆的MCP，传统UI自动化方式在逐步被新的AI取代，其存在的痛点也在逐步消失，随之也带来新的挑战。PageEyes随后将在落地实际业务场景上继续优化，借助AI提升测试效能。