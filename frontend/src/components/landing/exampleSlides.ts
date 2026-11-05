import type { SlideItem, SlideLayoutId } from "../../types";
import coverUrl from "../../assets/example/solar-cover.webp";
import earthUrl from "../../assets/example/earth-home.webp";

// Solar System example deck: 9 stable fixtures rendered through
// SLIDE_LAYOUTS with plain props (no v-html, no external hotlinks).
// Cover + Earth visuals are local Vite-bundled WebP assets.
// Copy lives in locales under landing.example.slides.* so the language
// switch re-renders; this module only maps keys to SlideItem shapes.

export const EXAMPLE_SLIDE_LAYOUTS: SlideLayoutId[] = [
  "hero_cover",
  "stats_flex",
  "cards_flex",
  "compare_2",
  "steps_flex",
  "chips_flex",
  "stat_hero",
  "takeaway",
  "split_media",
];

export type ExampleTranslator = (key: string) => string;

export function exampleSlideId(index: number): string {
  return `example-${index + 1}`;
}

function base(layout: SlideLayoutId, index: number, title: string, text: string): SlideItem {
  return {
    id: exampleSlideId(index),
    timestamp: 0,
    layout,
    title,
    text,
    bullets: [],
    keywords: [],
    filtered: false,
  };
}

export function buildExampleSlides(t: ExampleTranslator): SlideItem[] {
  const k = (key: string): string => t(`landing.example.slides.${key}`);
  return [
    {
      ...base("hero_cover", 0, k("s1.title"), ""),
      kicker: k("s1.kicker"),
      subtitle: k("s1.subtitle"),
      image: coverUrl,
    },
    {
      ...base("stats_flex", 1, k("s2.title"), ""),
      stats: [1, 2, 3, 4].map((n) => ({
        value: k(`s2.stat${n}Value`),
        label: k(`s2.stat${n}Label`),
      })),
    },
    {
      ...base("cards_flex", 2, k("s3.title"), ""),
      cards: [1, 2, 3, 4].map((n) => ({
        title: k(`s3.card${n}Title`),
        text: k(`s3.card${n}Text`),
      })),
    },
    {
      ...base("compare_2", 3, k("s4.title"), ""),
      cards: [1, 2].map((n) => ({
        title: k(`s4.card${n}Title`),
        text: k(`s4.card${n}Text`),
      })),
    },
    {
      ...base("steps_flex", 4, k("s5.title"), ""),
      steps: [k("s5.step1"), k("s5.step2"), k("s5.step3"), k("s5.step4")],
    },
    {
      ...base("chips_flex", 5, k("s6.title"), ""),
      chips: [k("s6.chip1"), k("s6.chip2"), k("s6.chip3"), k("s6.chip4")],
    },
    {
      ...base("stat_hero", 6, k("s7.title"), ""),
      stats: [{ value: k("s7.value"), label: k("s7.label") }],
    },
    {
      ...base("takeaway", 7, k("s8.title"), k("s8.text")),
    },
    {
      ...base("split_media", 8, k("s9.title"), k("s9.text")),
      image: earthUrl,
    },
  ];
}

export function buildExampleTranscripts(t: ExampleTranslator): string[] {
  return EXAMPLE_SLIDE_LAYOUTS.map(
    (_, i) => t(`landing.example.transcripts.t${i + 1}`),
  );
}
