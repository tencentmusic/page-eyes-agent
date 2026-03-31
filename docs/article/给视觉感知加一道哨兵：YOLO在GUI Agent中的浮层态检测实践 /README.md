# 给视觉感知加一道哨兵：GUI Agent 的浮层态检测实践

> OmniParser 很擅长解析页面上有什么元素，但它不擅长判断页面当前处于什么状态——有没有弹窗挡住主内容？
> 页面还在加载中吗？这些浮层如果不提前处理，Agent 的后续操作大概率会跑偏。
> 本文记录了我们如何训练一个轻量 YOLO 模型（Mac本地即可训练，最终产物只有5M，推理耗时平均60ms）。
> 将浮层态检测结果融合进 OmniParser 的解析链路，统一交给 Agent 决策，涵盖数据打标、离线增强、训练关键参数、测试效果分析

---

## 一、背景

GUI Agent 的执行链路可以简单拆成三层：感知、决策、执行。
在初期搭建 Agent 时，我们精心设计了决策层逻辑——LLM选型、Prompt工程、工具调用怎么设计。
感知层由OmniParserV2承担，由于OmniParserV2本身已经做得较完备，可识别页面上的所有元素。
但在落地GUI Agent一年多的实践过程中，我们持续录入了几百个UI智能巡检任务，感知层的问题开始以各种形式体现出来。

我们统计了一部分失败的顽固任务，发现背后原因是Agent对浮层的感知能力不足，即：**Agent 不知道当前界面处于什么状态**。
例如下图1和图2，刚打开页面，啪的一下弹出来一个弹窗，不点击关闭无法继续执行下一个操作，Agent只会报错找不到目标元素。
<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_2b26446a5ff98cd9f0dbeb02d6a4a19d5cfa6a4d.png" width="50%">
</div>

<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_f69c8dca10000f11a2e1255a4fe1dcc5a59f8245.png" width="50%">
</div>

或者如图3，冷启动或者网络波动导致的微信小程序打开速度较慢，页面加载了较长时间。但Agent不会等待，也会报错元素定位不到直接失败；
<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_ba216da37dcbc7aca9a5b30c8d3ecd9ab333ceab.png" width="50%">
</div>

因此，在GUI Agent执行链路中，我们希望加入一个浮层检测模块，Agent在执行任何操作之前，需要先判断清楚以下三类状态：

- 当前有没有弹窗（`dialog`）或操作面板（`bottom_sheet`）挡住主内容？
- 页面是否还在加载中（`loading`）？
- 有没有可以关闭的按钮（`close`）？

在弹窗小广告无孔不入的今天，Agent 被挡住主内容的情况越来越多，随之而来的痛点也越来越多。

**Loading 态的视觉形态极度多样。** 旋转菊花、骨架屏、进度条，我们的业务形态各异，涵盖PC Web端、移动端、微信小程序等，不同端的 Loading 样式不同。

**弹窗的位置和视觉形态千奇百怪。** 弹窗在移动端表现形式较多，有模态对话框、底部弹出层、悬浮弹窗，还有自定义弹窗。对于位置来说，如果训练数据里对图像做了垂直翻转，bottom_sheet 就变成了从顶部弹出，模型会学到完全错误的空间先验，在推理时把顶部导航栏也误判为 bottom_sheet。

**App的close 按钮越来越小。** 弹窗的关闭按钮，在 640×640 的输入图像中往往只占 20×20 像素左右，面积不到整图的 0.1%。轻量模型在小目标上本身就有局限，稍有不慎就会漏检，导致 Agent 以为弹窗无法关闭，陷入死循环。位置有时候隐藏在弹窗内，有时候在弹窗外。

**误报的代价比漏报更高。** 在 Agent 场景中，漏检一个 Loading 态，Agent 会等待超时后重试，损失的是时间。但误报一个不存在的弹窗，Agent 会尝试关闭它，可能触发错误的点击操作，导致业务流程跑偏，后续步骤全部失效

---

## 二、为什么不用其他方案

在收集了几十张失败任务截图的背景下，决定训练一个专用检测模型之前，我们调研且尝试了几条更省事的路。

**方案一：OCR + 规则。** 通过识别"加载中"、"请稍候"等文字来判断 Loading 态。对文字型 Loading 有效，但对纯动画型 Loading（旋转菊花、骨架屏）无能为力。而且强依赖语言，多语言 App 需要维护多套规则。对于弹窗态，基本无法覆盖。

**方案二：DinoV2（自回归模型）** 无监督学习，训练时不需要标注，可以解决图片打标的痛点，我们预期是喂给它整张图像，让它判断是否有弹窗，弹窗位置在哪。但本地尝试后发现效果并不理想，怀疑是由于收集图像数量较少，给模型的输入图像较复杂，相似特征较难提取，模型学习效果不佳。

**方案三：接入 VLM（视觉语言模型）** 测试了AutoGLM-Phone-9B模型的检测效果，通过自然语言描述来判断界面状态。零样本泛化能力强，对未见过的 UI 样式也有一定识别能力，
从测试效果来看，弹窗态和loading态的识别率达到90%以上。但对于高频的UI智能巡检任务系统来说，模型体积大，在端侧部署成本高。
更重要的是，我们的任务是固定的几个类别，不需要开放词汇的泛化能力，用 VLM 属于杀鸡焉用牛刀。

最终我们打算还是回到“传统方案”YOLO，且使用了其中参数量最小的 YOLOv11n。
YOLOv11n 参数量约 2.6M，满足 Agent 的实时性要求。
参数更大的变体（YOLOv11s、YOLOv11m）精度更高，但推理延迟会相应增加，在 Agent 的高频调用场景下不可接受。

---

## 三、数据质量

在开始打标之前，我们需要先确定训练数据的质量，搭建好的数据流水线处理结构如下，
整个流程分三个阶段，每个阶段有独立的脚本，职责清晰，可以单独重跑：

```
train_ori/（原始标注数据）
    ↓ split_dataset.py（8:2 划分，固定随机种子）
train/ + val/
    ↓ train_augment.py（离线增强）
augmented_train/
    ↓ merge_train_data.py（合并原始 + 增强）
merged_train/（最终训练集）
```

为了防止数据混用，需要遵守一个原则：**确保val 集只来自原始数据，不参与增强**。
如果增强数据混入 val 集，mAP 会虚高，掩盖真实的泛化能力问题。从指标来看以为模型已经很好了，但在真实截图上表现依然很差。


### 3.1 打标

打标工具使用 LabelImg，输出 YOLO 格式的 `.txt` 标签文件。

打标过程中，有几个原则是在踩坑之后才确立的：

**框要紧，不要松。** GUI 元素边界清晰，没有理由框松。框松的标注会让模型学到"元素周围的背景也是目标的一部分"，导致推理时的定位精度下降，IoU 指标虚高但实际可用性差。

**分类策略优先考虑视觉特征。** 每个类别应该有明确视觉特征或容易区分，早期训练时我们尝试基于UI设计元素区分，如"center dialog"、"modal dialog"、"alert dialog"，"toast"等，
实际上语义绑定很重，视觉特征的区分度并不高，导致效果并不好。
第二版我们粗略地简化为两类，如"dialog"、"bottom_sheet"，主要靠位置区分，特征差异明显。

**负样本引入。** 从微调Florence2模型和训练yolov11n模型的经验来看，负样本不可或缺。如果只有正样本，训练出来的模型在普通页面上误报率极高——它会把列表页的卡片误判为 dialog，把页面顶部的导航栏误判为 bottom_sheet。负样本数量建议占总数据量的 20%~30%。

---

## 四、数据策略-离线增强

由于收集的图像实在太少，我们使用了离线增强的方法来扩大训练数据量，增强策略如下：

### 4.1 增强策略选取

在 GUI 场景中，有几类通用增强方法是明确有害的，必须禁用：

**旋转和翻转。** GUI 截图永远是水平的，App 界面不会倾斜，不会上下颠倒。训练配置中 `degrees: 0.0`、`fliplr: 0.0`、`flipud: 0.0`，全部禁用。

**auto_augment。** Ultralytics 的 `auto_augment` 支持 `randaugment`、`autoaugment`、`augmix` 等策略，这些策略内部包含了旋转、翻转等操作，将显式设置为空字符串，可有效避免自增强带来的负面影响


### 4.2 正样本增强方式

明确增强策略后，我们采取了以下方式进行增强：

**几何微变形（Affine）**

**亮度/对比度（OneOf 互斥选择）**

**色彩偏移（OneOf 互斥选择）**：HSV 偏移和 RGB 偏移互斥选择

**压缩/下采样（OneOf 互斥选择）**：JPEG 压缩和下采样互斥选择

**锐化/模糊（OneOf 互斥选择）**：低概率（40%）、低强度

### 4.3 正负样本量级差异化

```python
POS_AUG_TIMES = 6   # 正样本增强 6 倍
NEG_AUG_TIMES = 3   # 负样本增强 3 倍
```

设置正样本的增强倍数更高，让模型学习正样本的视觉模式，同时避免负样本在训练集中占比过高，
导致模型过于保守——倾向于把所有东西都预测为背景，漏检率上升。

---

## 五、训练

数据准备好之后，训练yolo代码其实不复杂，以下仅针对关键配置做说明：

### 5.1 模型选型

第二节已经说明了选 YOLOv11n 的原因：参数量约 2.6M，推理延迟在 Mac 本地单张图像约 15~30ms，满足 Agent 高频调用的实时性要求。
这里补充一点：YOLOv11n 使用的是 ImageNet 预训练权重，底层的边缘、纹理、颜色特征已经收敛，在 GUI 截图这种视觉结构清晰的场景下，迁移学习的起点很高，不需要从零开始。

我们没有选择更大的变体（YOLOv11s、YOLOv11m），也没有选择更小的自定义架构。前者推理成本不可接受，后者需要重新设计 Head 层，工程成本远超收益。


### 5.2 训练参数设计

训练在 Mac 本地跑，使用 MPS 加速（Apple Silicon GPU），整个过程完全不需要云端 GPU，这也是选 YOLOv11n 而非更大变体的直接原因之一。

几个关键参数的设计思路：

**Epoch 设置为 130**：对于这种量级的小数据集（我们使用的训练样本总数为700+），Epoch 不需要太多。预训练权重已经提供了很好的特征起点，微调阶段的任务是让模型适应 GUI 截图的分布，而不是从头学习视觉特征。Epoch 过多反而容易把预训练学到的通用特征"练废"，在验证集上开始过拟合。
130 是在本地几次实验后确定的经验值，在 Mac 本地训练完成只需要 1~2 小时。

**Patience 设置为 50**：Ultralytics 的 Early Stopping 机制会在验证集 mAP 连续 patience 个 Epoch 不再提升时自动停止训练，取最优权重。
确保最终保存的 `best.pt` 是验证集上表现最好的那个检查点，而不是最后一个 Epoch 的权重。

**Image Size 固定为 640**：YOLO 的默认输入尺寸，与预训练权重对齐。

**Batch Size 设置为 16**：在 Mac 本地 MPS 加速下，batch=16 是内存和速度的平衡点。
batch 太小（如 4、8）会导致 BatchNorm 层的统计量不稳定，训练波动大；batch 太大在 Mac 上会触发内存压力，反而变慢。


### 5.3 部署

训练完成后，直接使用 Ultralytics 保存的最优权重 `best.pt` 进行推理，无需额外的导出步骤。`best.pt` 文件约 5MB，可以直接随 Agent 代码一起分发。

融合进 OmniParser 的方式很直接：
在 OmniParser 完成页面元素解析之后，额外跑一次浮层检测推理，将检测结果（类别 + 置信度 + 坐标）附加到解析结果里，统一交给 Agent 的决策层。
Agent 侧增加了一个专门的弹窗处理 Skill：收到解析结果后，先检查是否有弹窗，如果有，根据弹窗关闭按钮坐标点击关闭；如果有 `loading`，等待后重试。

---

## 六、效果展示与分析

模型训练完成后，评估不能仅仅是训练过程中的mAP指标, 还需结合真实业务场景使用效果，
我们在本地批量跑了100张真实业务截图，覆盖 PC Web、移动端 H5、微信小程序三种端形态，
从中取典型案例进行分析。


### 6.1 TP/TN/FP/FN

我们基于分类精度评价领域的四个概念，来衡量一个模型的有效性：

| | 预测为正样本 | 预测为负样本 |
|---|---|---|
| **实际为正样本** | TP（正确检出） | FN（漏检） |
| **实际为负样本** | FP（误报） | TN（正确排除） |

精确率衡量的是"预测为正的里面有多少是真正的正"，
召回率衡量的是"真正的正里面有多少被检出来了"。
两者通常是此消彼长的关系，阈值越低，召回率越高，但误报也越多；阈值越高，精确率越高，但漏检也越多。

在 Agent 场景中，FP 和 FN 的代价不一样：

- **FN（漏检）**：Agent 没有感知到弹窗，会继续执行后续操作。弹窗漏检会导致 Agent 尝试操作被遮挡的主内容，操作大概率失败。
- **FP（误报）**：Agent 误以为存在弹窗，但本身是一个正常页面，Agent 会陷入"找不到关闭按钮"的异常分支，中断当前任务流程。如果误报位置恰好有其他可点击元素，Agent 可能触发错误操作，导致业务流程跑偏，后续步骤全部失效。

FP的代价高于FN。这也是我们选择 0.36 的置信度阈值的原因，在召回率和精确率之间向精确率倾斜。


### 6.2 检测结果分析&融合结果

**弹窗及弹窗关闭按钮检测（`dialog` / `bottom_sheet` / `close`）**

弹窗类是整体表现较稳定的类别，

`dialog`（模态弹窗）通常居中显示、有明显的阴影遮罩层，视觉特征强，TP 率较高。
典型 FP 场景是页面中存在大面积卡片组件（Card），背景色与弹窗相近且有圆角和阴影，
模型偶尔会将其误判为 dialog。比如下面浪潮榜的海报页面，其歌曲封面为空，展示的是一个默认的歌曲封面图，模型误判为 dialog
<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_45614190cdb5bb456ff8f153384c8fb743a327ac.jpg" width="50%">
</div>


`bottom_sheet`（底部弹出层）是所有类别中最难检测的。
TP 的核心特征是从屏幕底部向上弹出，模型在这类标准形态上表现良好。
FN 的主要来源是： bottom_sheet 展开高度超过屏幕 70%，视觉上已接近全屏，
模型无法从局部特征判断这是一个浮层；二是某些 App 的 bottom_sheet 没有圆角和拖拽条，
视觉上与普通页面几乎无法区分。 如下面2个图所示，分别对应我们分析的这2类场景。

<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_e4f6ab6b9180651be9fef1a4f84aa78e9c7095df.jpg" width="50%">
</div>

<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_d529be95d7d9913be834c6a641c36e49b95875c4.jpg" width="50%">
</div>

close 按钮的面积最小，TP 的典型场景为：弹窗右上角或弹窗下方的 × 号，尺寸一般小于48×48 像素，模型在测试集范围内表现稳定。
<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_ddaf7b556c88295b26eefd85da5fa1bacb4a918a.jpg" width="50%">
</div>
---

**`loading`（加载态）**

Loading 态是误报率最低的类别。推测原因是：从视觉特征上，Loading 态的核心特征（如旋转菊花、骨架屏的灰色渐变块、进度条的填充等）通常有迹可循：
旋转菊花通常有特定的辐射状结构，骨架屏有规律的灰色矩形占位块。

TP 覆盖了我们业务中最常见的三种 Loading 形态：旋转菊花、骨架屏、局部区域的 Loading 占位。
FP 几乎没有。Loading 态的视觉特征足够独特，在非 Loading 页面上几乎不会触发误报。
<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_78b5bb4a453e5d6cbc5ac97b98cda0512f364acc.jpg" width="50%">
</div>

<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_99c0207203b186962c7abc1e70d4cccb96a4830d.jpg" width="50%">
</div>

---


**融合结果展示**

我们改造了OmniParser，在它的识别解析结果中融合了浮层态检测模块的推理结果，对应GUI Agent添加了专门的弹窗处理Skills，已经接入使用。

<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_5692a1475b36dd10477816834372989f036f8681.png" width="50%">
</div>

<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_8ae2c68dfb075f1ec6b3cf96f25de3e372de99d9.png" width="50%">
</div>
<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_2d59acfafef33cbf5750d35465596cff41a1bc73.png" width="50%">
</div>
<div align="center">
<img src="https://cdn-y.tencentmusic.com/uni/commonPic/cos_8d929f21778994fffb2c037a90c8b238a735c0f8.png" width="50%">
</div>
当前版本在真实业务截图上的误报率控制在可接受范围内，Agent 的浮层处理成功率相比没有检测模块时有明显提升。

整个训练流程在 Mac 本地完成，无需 GPU 服务器，最终的模型产物不到 5MB，
融合到OmniParser的识别解析结果中后，推理延迟在单张图像上约为 50~70ms，满足 Agent 的实时性要求。


---
