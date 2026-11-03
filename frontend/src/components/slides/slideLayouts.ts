import type { Component } from "vue";
import type { SlideLayoutId } from "../../types";
import SlideCardsFlex from "./SlideCardsFlex.vue";
import SlideChecklistFlex from "./SlideChecklistFlex.vue";
import SlideChipsFlex from "./SlideChipsFlex.vue";
import SlideCompare from "./SlideCompare.vue";
import SlideHeroCover from "./SlideHeroCover.vue";
import SlideQuote from "./SlideQuote.vue";
import SlideSeparator from "./SlideSeparator.vue";
import SlideSplitCode from "./SlideSplitCode.vue";
import SlideStatsFlex from "./SlideStatsFlex.vue";
import SlideStepsFlex from "./SlideStepsFlex.vue";
import SlideTextImage from "./SlideTextImage.vue";
import SlideTitleBullets from "./SlideTitleBullets.vue";
import SlideTitleText from "./SlideTitleText.vue";

export const SLIDE_LAYOUTS: Record<
  SlideLayoutId,
  { label: string; component: Component }
> = {
  title_text: { label: "Título + texto", component: SlideTitleText },
  title_bullets: { label: "Título + bullets", component: SlideTitleBullets },
  text_image: { label: "Texto + imagen", component: SlideTextImage },
  quote: { label: "Cita destacada", component: SlideQuote },
  hero_cover: { label: "Hero cover", component: SlideHeroCover },
  cards_flex: { label: "Cards grid", component: SlideCardsFlex },
  split_code: { label: "Split code", component: SlideSplitCode },
  split_media: { label: "Split media", component: SlideTextImage },
  separator: { label: "Separator", component: SlideSeparator },
  compare_2: { label: "Compare", component: SlideCompare },
  checklist_flex: { label: "Checklist", component: SlideChecklistFlex },
  stats_flex: { label: "Stats", component: SlideStatsFlex },
  chips_flex: { label: "Chips", component: SlideChipsFlex },
  bullets_flex: { label: "Bullets", component: SlideTitleBullets },
  steps_flex: { label: "Steps", component: SlideStepsFlex },
  definition_guided: { label: "Definition guided", component: SlideTitleText },
  concept_editorial: { label: "Concept editorial", component: SlideTitleText },
  pillars_3: { label: "Pillars 3", component: SlideCardsFlex },
  timeline_4: { label: "Timeline 4", component: SlideStepsFlex },
  takeaway: { label: "Takeaway", component: SlideQuote },
  stat_hero: { label: "Stat hero", component: SlideStatsFlex },
};
