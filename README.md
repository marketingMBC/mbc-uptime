# mbc-uptime — monitor de sitios de Meta Build City

Cada 5 minutos GitHub Actions revisa los sitios de `sites.json`. Si uno cae (no resuelve,
HTTP ≥ 400, certificado inválido o por vencer en < 14 días), tras una segunda prueba a los
30 s:

1. abre un issue **«🔴 Caído: host»** con el motivo, el proyecto Vercel y el registro DNS
   (GitHub manda correo al dueño del repo), y
2. avisa por Telegram (`@Metabuild_claude_bot`).

Cuando vuelve, cierra el issue y avisa **«🟢 Recuperado»**. Solo alerta en el cambio de
estado. Corre en GitHub Actions y no en n8n para no gastar créditos de n8n; el repo es
público porque así los minutos son gratis (solo contiene URLs públicas; los tokens son
secrets del repo).

Agregar un sitio = agregar una línea a `sites.json`.

## Inventario DNS de `metabuild.city` (GoDaddy)

GoDaddy no permite ponerle nombre o nota a un registro, así que la identificación vive aquí.
**`@` significa «el dominio pelado»** (`metabuild.city` sin nada delante); es la convención
de todo DNS, no se puede renombrar. El de `@` tiene que ser tipo **A** (una IP) porque un
dominio raíz no admite CNAME; todos los subdominios son **CNAME** al destino que da Vercel.

| Tipo | Nombre | Dirección pública | Qué es | Proyecto Vercel |
|---|---|---|---|---|
| A | `@` | metabuild.city | Sitio corporativo MBC | `metabuild-website` |
| CNAME | `www` | www.metabuild.city | Sitio corporativo MBC | `metabuild-website` |
| CNAME | `hub` | hub.metabuild.city | Metabuild HUB | `metabuild-hub` |
| CNAME | `agents` | agents.metabuild.city | Metabuild Agents | `metabuild-agents` |
| CNAME | `bim` | bim.metabuild.city | Metabuild BIM | `metabuild-bim` |
| CNAME | `sport` | sport.metabuild.city | Metabuild Sport | `metabuild-sport-platform` |
| TXT | `@` | — | Verificación de dominio de Anthropic | — |
| CNAME | `_domainconnect` | — | Interno de GoDaddy (conexión automática) | — |
| NS / SOA | `@` | — | Servidores de GoDaddy (no tocar) | — |

`metabuildcity.com` solo redirige 301 a `https://metabuild.city/`.

### Regla de oro

Para conectar un subdominio nuevo: **«Añadir un registro nuevo»**, nunca editar uno
existente. Las dos caídas del 17 y 19-oct-2026 vinieron de editar el registro de `@` o el de
`sport` en vez de agregar uno nuevo. El destino exacto del CNAME lo da Vercel
(`Settings › Domains` del proyecto); si el certificado no sale solo:
`vercel certs issue <dominio>`.
