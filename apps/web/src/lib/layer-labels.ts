/** Plain-language labels for pipeline layers (IDs kept for API/code). */

export interface LayerLabel {
  title: string;
  short: string;
}

export const LAYER_LABELS: Record<string, LayerLabel> = {
  L1: { title: "抓取商品", short: "抓取" },
  L2: { title: "智能写脚本", short: "脚本" },
  L3: { title: "分镜编排", short: "分镜" },
  L4: { title: "视频渲染", short: "渲染" },
  L5: { title: "任务调度", short: "调度" },
  L6: { title: "质量检测", short: "质检" },
  L7: { title: "多平台发布", short: "发布" },
  L8: { title: "效果数据", short: "数据" },
};

export function layerTitle(layerId: string): string {
  return LAYER_LABELS[layerId]?.title ?? layerId;
}

export function layerShort(layerId: string): string {
  return LAYER_LABELS[layerId]?.short ?? layerId;
}
