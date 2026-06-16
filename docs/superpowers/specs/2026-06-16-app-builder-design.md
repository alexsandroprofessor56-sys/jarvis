# AppBuilder — Gerador Autônomo de Apps/Sites

## Resumo

Jarvis ganha a capacidade de criar aplicativos e sites completos a partir de
descrições em linguagem natural. O AppBuilder decide autonomamente o tipo de
projeto (PWA, site estático, APK Flutter), gera o código, faz o build e
deploy, e entrega o resultado ao usuário via Telegram/tela.

## Arquitetura

```
agent/app_builder.py          → Orquestrador principal
agent/app_builder_site.py     → Gerador de sites estáticos
agent/app_builder_pwa.py      → Gerador de PWA (service worker + manifest)
agent/app_builder_flutter.py  → Gerador de APK Flutter
app_templates/                → Templates base para cada tipo
```

### Fluxo

1. Usuario envia descrição (ex: "cria um app de tarefas com banco SQLite")
2. AppBuilder.analyze() → LLM decide: tipo, framework, features
3. AppBuilder.scaffold() → copia template, estrutura pastas
4. AppBuilder.generate() → LLM gera/customiza cada arquivo
5. AppBuilder.build() → executa build command
6. AppBuilder.deploy() → sobe pra hospedagem ou gera APK
7. AppBuilder.deliver() → envia URL/APK pro usuário

## Tipos de Projeto

### Site Estático (HTML/CSS/JS)
- Template vanilla ou com framework leve
- Deploy: GitHub Pages, Netlify, ou servidor HTTP local
- Build: nenhum (só copiar arquivos)

### PWA (Progressive Web App)
- Template com service worker + manifest.json + ícones
- Deploy: GitHub Pages ou Netlify
- APK via Bubblewrap: `npx @pwabuilder/cli package`
- Build: gerar service worker, otimizar assets

### APK Flutter
- `flutter create` com template base
- LLM customiza `main.dart`, `pubspec.yaml`, telas
- Build: `flutter build apk --release`
- APK salvo em `build/app/outputs/flutter-apk/`

## Deployers

| Deployer | Alvo | Comando |
|----------|------|---------|
| GitHubPages | github.io | `git push` + enable Pages via `gh` |
| Netlify | netlify.app | `npx netlify-cli deploy` |
| LocalHTTP | localhost | Servidor Python embutido |

O LLM escolhe o deployer baseado no tipo de projeto e disponibilidade.

## Armazenamento

Projetos salvos em `~/.jarvis/projects/<nome-do-projeto>/` com:
- `project.json` — metadados (tipo, status, URL, datas)
- `src/` — código fonte
- `dist/` — artefatos buildados

## Ferramentas (Tools)

| Tool | Descrição |
|------|-----------|
| `app_builder` | Ponto de entrada: "cria um app de lista de tarefas" |
| `app_status` | Ver status de projetos em andamento |
| `app_list` | Listar todos os projetos criados |
| `app_deploy` | Fazer deploy de um projeto existente |

## Integrações

- **Telegram**: Recebe comando, envia resultado (URL/APK)
- **ComputerUse**: Fallback para login em serviços que precisam de navegador
- **Credential Vault**: Para API keys de deploy (Netlify, GitHub token)
- **Knowledge Base**: Aprende com projetos anteriores para melhorar geração

## Limitações Conhecidas

- Modelo qwen2.5:3b tem capacidade limitada para gerar código complexo
- Flutter SDK precisa ser instalado (~1.5GB)
- APK via Bubblewrap (PWA→APK) não tem todas features nativas
- Deploy em produção real requer contas em serviços externos

## Critérios de Sucesso

1. `app_builder("cria um site pessoal")` → site HTML/CSS no GitHub Pages
2. `app_builder("cria um app PWA de clima")` → PWA com service worker + deploy
3. `app_builder("cria um app Android de calculadora")` → APK Flutter funcional
4. Projetos entregues ao usuário com URL/APK em < 10 minutos
