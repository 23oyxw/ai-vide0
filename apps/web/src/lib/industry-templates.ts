/** Industry presets + model/styles for demo / interview flows. */

export interface IndustryTemplate {
  id: string;
  name: string;
  category: string;
  productUrl: string;
  painPoints: string[];
  topicHint: string;
  scriptHints: string;
}

export interface VideoStyle {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export const INDUSTRY_TEMPLATES: IndustryTemplate[] = [
  {
    id: "home", name: "家居收纳", category: "家居日用",
    productUrl: "https://item.taobao.com/item.htm?id=home-demo",
    painPoints: ["收纳空间不足", "小户型难整理", "颜值与实用难兼顾"],
    topicHint: "小户型收纳神器实测：3 秒变整洁",
    scriptHints: "1. 钩子（0-3s）：打开乱糟糟的抽屉\n2. 痛点（3-7s）：空间小、东西多、找不到\n3. 特写（7-12s）：分层收纳·承重展示\n4. CTA（12-15s）：限时优惠，点击小黄车",
  },
  {
    id: "beauty", name: "美妆护肤", category: "美妆个护",
    productUrl: "https://item.jd.com/beauty-demo.html",
    painPoints: ["卡粉浮粉", "持妆时间短", "敏感肌不敢试"],
    topicHint: "平价底妆救星：干皮实测 8 小时不脱妆",
    scriptHints: "1. 钩子（0-3s）：左右脸对比·妆前妆后\n2. 痛点（3-7s）：卡粉·暗沉·补妆频繁\n3. 特写（7-12s）：质地·遮瑕·持妆测试\n4. CTA（12-15s）：新人券立减，链接在评论区",
  },
  {
    id: "shoes", name: "鞋服穿搭", category: "鞋服配饰",
    productUrl: "https://detail.tmall.com/item.htm?id=shoes-demo",
    painPoints: ["磨脚挤脚", "走路累", "搭配难"],
    topicHint: "通勤暴走鞋：软底缓震一天不累",
    scriptHints: "1. 钩子（0-3s）：地铁换乘暴走 1 万步\n2. 痛点（3-7s）：硬底累脚·磨后跟\n3. 特写（7-12s）：缓震中底·透气网面·百搭配色\n4. CTA（12-15s）：尺码表在详情页",
  },
  {
    id: "kitchen", name: "厨房好物", category: "厨房家电",
    productUrl: "https://item.jd.com/kitchen-demo.html",
    painPoints: ["做饭费时", "油烟大难清洁", "厨房太小施展不开"],
    topicHint: "懒人厨房神器：5 分钟搞定一餐",
    scriptHints: "1. 钩子（0-3s）：下班回家不想做饭的绝望\n2. 痛点（3-7s）：备菜麻烦·油烟呛人·洗碗崩溃\n3. 特写（7-12s）：一体多功能·快速加热·易清洗\n4. CTA（12-15s）：新品尝鲜价，点链接下单",
  },
  {
    id: "digital", name: "数码电子", category: "数码配件",
    productUrl: "https://item.jd.com/digital-demo.html",
    painPoints: ["续航焦虑", "携带不便", "性价比不高"],
    topicHint: "百元级真无线耳机：续航 30 小时实测",
    scriptHints: "1. 钩子（0-3s）：掏出没电的耳机一脸无奈\n2. 痛点（3-7s）：续航短·连着线·音质差\n3. 特写（7-12s）：充电仓续航·小巧设计·无损音质\n4. CTA（12-15s）：限时特价，点击链接",
  },
  {
    id: "baby", name: "母婴用品", category: "母婴",
    productUrl: "https://item.taobao.com/item.htm?id=baby-demo",
    painPoints: ["安全性担忧", "材质是否无害", "性价比"],
    topicHint: "宝妈实测：这款湿巾无限回购",
    scriptHints: "1. 钩子（0-3s）：宝宝吃完辅食满嘴都是\n2. 痛点（3-7s）：含酒精·掉絮·太薄\n3. 特写（7-12s）：EDI 纯水·珍珠纹·厚实柔韧\n4. CTA（12-15s）：宝妈福利价，多囤多省",
  },
];

export const VIDEO_STYLES: VideoStyle[] = [
  { id: "real", name: "真人出镜", icon: "👩", description: "暖色对话风·第一人称·生活场景" },
  { id: "product", name: "纯产品", icon: "📦", description: "极简白底·参数展示·冷静客观" },
  { id: "3d", name: "3D 动画", icon: "🎬", description: "暗黑科技·360°旋转·未来感" },
  { id: "unbox", name: "开箱测评", icon: "📦", description: "桌面记录·包裹拆箱·真实体验" },
  { id: "compare", name: "对比测评", icon: "⚖️", description: "分屏对比·数据驱动·A vs B" },
];

export interface VideoTemplate { id: string; name: string; seconds: number; description: string; }
export const VIDEO_TEMPLATES: VideoTemplate[] = [
  { id: "motion_poster", name: "快闪", seconds: 5, description: "5 秒动态海报，适合首屏引流" },
  { id: "post_production_15s_zhongcao", name: "种草", seconds: 15, description: "15 秒标准竖屏种草视频" },
  { id: "product_ad", name: "广告", seconds: 30, description: "30 秒产品 TVC 广告" },
];
