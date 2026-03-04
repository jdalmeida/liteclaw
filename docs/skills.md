# Skills

Skills são instruções em markdown que ensinam o modelo a usar tools. Formato compatível com [AgentSkills](https://agentskills.io/).

## Estrutura

Cada skill é um diretório com `SKILL.md`:

```
skills/
└── minha_skill/
    └── SKILL.md
```

## Formato SKILL.md

```markdown
---
name: minha-skill
description: Descrição curta para o modelo
metadata: {"openclaw":{"requires":{"bins":["comando"]}}}
---
Instruções em markdown para o modelo...
```

### Frontmatter

- **name** — identificador da skill
- **description** — descrição exibida ao modelo
- **metadata** — JSON com gating (opcional)

### Gating (metadata.openclaw.requires)

A skill só é carregada se os requisitos forem atendidos:

- **bins** — lista de binários que devem existir no PATH
- **env** — variáveis de ambiente obrigatórias
- **config** — caminhos em config que devem ser truthy
- **anyBins** — pelo menos um binário deve existir

Exemplo:

```markdown
---
name: web-search
description: Busca na web
metadata: {"openclaw":{"requires":{"env":["BRAVE_API_KEY"]}}}
---
Use web_search para buscar informações na web.
```

## Locais de carregamento

Precedência (maior → menor):

1. **Workspace** — `./skills` ou `{workspace}/skills`
2. **Managed** — `~/.liteclaw/skills`
3. **Bundled** — `liteclaw/bundled_skills`
4. **Extra** — configurável via `skills.load.extraDirs`

Em conflito de nome, o primeiro vence.

## Desabilitar skill

Em `~/.liteclaw/config.json`:

```json
{
  "skills": {
    "entries": {
      "minha-skill": { "enabled": false }
    }
  }
}
```

## Uso no Agent

O `SkillsLoader` carrega as skills elegíveis e formata em XML para injeção no system prompt. O modelo vê a lista de skills disponíveis e suas descrições.
