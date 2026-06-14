---
sidebar_position: 7
title: "Mixture of Agents"
description: "Use /moa presets to run prompts through multiple configured models inside the normal Hermes agent loop"
---

# Mixture of Agents

Mixture of Agents is a slash-command execution mode, not a model tool and not a provider. Your selected main model still emits the final assistant message and tool calls. MoA reference models and the aggregator produce private guidance before each main-model iteration.

Use it when a hard task benefits from multiple model perspectives but still needs Hermes' normal agent loop: tool calls, follow-up iterations, interrupts, transcript persistence, and the same session context as any other message.

## Slash command behavior

```bash
/moa
```

Toggles the default MoA preset on or off for the current session.

```bash
/moa review
```

If `review` exactly matches a preset name, Hermes toggles that preset. If another preset is already active, Hermes switches to `review`.

```bash
/moa design and implement a migration plan for this flaky test cluster
```

If the text does not exactly match a preset name, Hermes treats it as a one-shot prompt. The prompt runs through MoA once, then MoA turns off again.

Preset matching is exact on purpose. Hermes does not fuzzy-match preset names, so normal prompts cannot accidentally become persistent toggles.

## How it works in the agent loop

For a `/moa` turn, Hermes:

1. runs the configured reference models;
2. runs the configured aggregator model to synthesize private guidance;
3. injects that guidance into the current normal agent-loop iteration;
4. lets the main model respond or call tools normally;
5. if tools run, appends the tool results to the conversation;
6. runs MoA again before the next main-model iteration, so tool results feed the next MoA pass.

This also composes with `/goal`: if a session has an active MoA preset, goal continuation turns inherit that preset.

## Configure presets

You can configure named MoA presets from:

- Dashboard → Models → Model Settings → Mixture of Agents
- Desktop app → Settings → Model → Mixture of Agents
- Desktop app model/status menu → MoA presets (session toggle)
- `hermes moa configure [name]`
- `config.yaml`

The config stores explicit provider/model pairs, so you can mix providers and use multiple models from the same provider:

```yaml
moa:
  default_preset: default
  active_preset: ""
  presets:
    default:
      reference_models:
        - provider: openai-codex
          model: gpt-5.5
        - provider: openrouter
          model: deepseek/deepseek-v4-pro
      aggregator:
        provider: openrouter
        model: anthropic/claude-opus-4.8
      reference_temperature: 0.6
      aggregator_temperature: 0.4
      max_tokens: 4096
      enabled: true
```

Default preset:

- reference: `openai-codex:gpt-5.5`
- reference: `openrouter:deepseek/deepseek-v4-pro`
- aggregator: `openrouter:anthropic/claude-opus-4.8`

## Terminal preset management

```bash
hermes moa list
hermes moa configure              # update the default preset
hermes moa configure review       # create or update a named preset
hermes moa delete review
```

## Notes

- MoA is no longer listed under `hermes tools`; there is no `moa` toolset to enable.
- Credential failures on one reference model do not abort the turn. Hermes includes the failure in the synthesis context and continues with whatever models returned.
- MoA increases model-call count. A single main-model iteration can involve multiple reference calls plus the aggregator call before the main model is invoked.
