# Output schemas

## transcript.json

```json
[
  {"start": 0.0, "end": 5.2, "text": "..."}
]
```

## summary.json

```json
{
  "title": "",
  "source_url": "",
  "tldr": [""],
  "chapters": [
    {
      "start": 0.0,
      "end": 120.0,
      "title": "",
      "summary": "",
      "key_points": [
        {
          "label": "[FACT] | [AUTHOR_VIEW] | [MODEL_INFERENCE]",
          "text": "",
          "evidence_timestamps": [0.0]
        }
      ]
    }
  ],
  "action_items": [""],
  "review_questions": [""]
}
```

## debate.json

```json
{
  "author_view": [
    {"claim": "", "evidence_timestamps": [0.0]}
  ],
  "skeptic_view": [
    {"issue": "", "why_it_matters": "", "evidence_timestamps": [0.0]}
  ],
  "counter_view": [
    {"claim": "", "supporting_reason": ""}
  ],
  "judge": {
    "useful_parts": [""],
    "questionable_parts": [""],
    "what_to_verify_next": [""],
    "overall_confidence": 0.0
  }
}
```

## frame_plan.json

```json
[
  {
    "timestamp": 754.0,
    "topic": "",
    "reason": "",
    "evidence_quote": "",
    "need_frame": true,
    "window_seconds": 8
  }
]
```

## frames/selected_frames.json

```json
[
  {
    "timestamp": 754.0,
    "topic": "",
    "selected_frame": "frames/keyframe_001_t+0.jpg",
    "caption": "",
    "why_selected": ""
  }
]
```

## image_prompts.json

```json
[
  {
    "id": "sketch_map_01",
    "type": "xiaohei_contraption | xiaohei_judgment_machine",
    "title": "",
    "prompt": "内置 imagegen 中文手绘风图片提示词...",
    "size": "1600x900"
  }
]
```

## generated_images.json

```json
[
  {
    "id": "sketch_map_01",
    "title": "小黑价格筛选机",
    "path": "generated/sketch_map_01.png",
    "type": "built_in_imagegen_png",
    "model": "image_gen",
    "source": "~/.codex/generated_images/.../image.png"
  }
]
```

## lesson_units.json

```json
[
  {
    "id": "lesson_01",
    "chapter_index": 1,
    "title": "",
    "objective": "",
    "explanation": "",
    "procedure": [""],
    "common_mistakes": [""],
    "verification_conditions": [""],
    "my_handling": "",
    "visuals": [
      {
        "frame": "frames/keyframe_001.jpg",
        "caption": "",
        "what_to_look_at": [""]
      }
    ],
    "checkpoint": {
      "question": "",
      "answer": "",
      "rubric": ""
    }
  }
]
```

## visual_storyboard.json

```json
[
  {
    "timestamp": 754.0,
    "chapter_index": 3,
    "frame": "frames/keyframe_001.jpg",
    "visual_type": "chart_example | source_moment",
    "teaching_role": "",
    "must_explain": true,
    "objects": ["PD Array"],
    "replacement_text": "",
    "needs_annotation": false
  }
]
```

## assessment.json

```json
{
  "mastery_threshold": 0.8,
  "quiz": [
    {
      "id": "q_01",
      "type": "single_choice",
      "question": "",
      "options": ["", "", "", ""],
      "answer_index": 0,
      "explanation": "",
      "lesson_ref": ""
    }
  ],
  "score_bands": [
    {"min": 0.8, "label": "完成学习", "advice": ""}
  ]
}
```

## asset_health.json

```json
{
  "checked_at": "2026-07-04T12:00:00",
  "total": 0,
  "ok": true,
  "missing_or_invalid": [],
  "assets": [
    {
      "path": "generated/sketch_map_01.png",
      "exists": true,
      "size": 1024,
      "decodable": true
    }
  ]
}
```

## replacement_review.json

```json
{
  "created_at": "2026-07-04T12:00:00",
  "replacement_score": 85,
  "replacement_ready": true,
  "score_breakdown": {
    "content_completeness": 25,
    "visual_replacement": 25,
    "practice_answers": 20,
    "critical_review": 15,
    "reading_experience": 15
  },
  "threshold": 85,
  "fail_reasons": []
}
```

## run_review.json

```json
{
  "created_at": "2026-07-04T12:00:00",
  "mode": "safe | authorized",
  "source": "",
  "transcript_segments": 0,
  "chapters": 0,
  "frame_plan_items": 0,
  "saved_frames": false,
  "label_coverage": {
    "[FACT]": true,
    "[AUTHOR_VIEW]": true,
    "[MODEL_INFERENCE]": true,
    "[COUNTERPOINT]": true,
    "[JUDGMENT]": true
  },
  "scores": {
    "summary_coverage": 0.0,
    "timestamp_evidence_quality": 0.0,
    "boundary_compliance": 1.0,
    "reviewability": 1.0
  },
  "next_optimization_suggestions": [""]
}
```

## notes_for_next_run.md

Markdown audit note for local learning only. It should summarize source, transcript size, generated chapter count, safe-mode boundary compliance, and suggested manual improvements. Do not use it to automatically rewrite `SKILL.md`.
