# 📦 Empacotar e criptografar o SafeRoute

Como gerar um arquivo `.zip` (ou `.7z`) do projeto pra entregar (PUC, backup,
etc.) e protegê-lo com senha forte.

---

## ⚠️ Antes de empacotar — checklist de segurança

```powershell
cd "C:\Users\calil\Downloads\CLAUDE CODE\saferoute-melhorado"

# 1. Garante que .env NÃO vai entrar no zip
Get-ChildItem -Force | Where-Object Name -eq ".env"
# Se aparecer, ele EXISTE local. NÃO commite, mas pode entrar no zip
# se você quiser entregar o ambiente completo. AVISE o destinatário.

# 2. Limpa banco local + caches gerados (opcional, mas recomendo)
Remove-Item -Recurse -Force instance, data\saferoute.db, data\geocode_cache.db, data\analytics.db -ErrorAction SilentlyContinue

# 3. Limpa __pycache__
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
```

---

## Opção A — ZIP simples (sem criptografia)

> ⚠️ ZIP padrão do Windows é fraco e o "Adicionar senha" é ignorado por
> ferramentas modernas. Use só pra arquivos não sensíveis.

```powershell
cd "C:\Users\calil\Downloads\CLAUDE CODE"
Compress-Archive -Path saferoute-melhorado -DestinationPath saferoute-v2.zip
```

---

## Opção B — 7-Zip com AES-256 (RECOMENDADO)

7-Zip oferece criptografia **AES-256** robusta, que protege também os
nomes dos arquivos. Funciona em Windows, macOS e Linux.

### Instalar 7-Zip
https://www.7-zip.org/ → versão 64-bit

### Criar 7z criptografado

```powershell
cd "C:\Users\calil\Downloads\CLAUDE CODE"

& "C:\Program Files\7-Zip\7z.exe" a -t7z -mhe=on -p saferoute-v2.7z saferoute-melhorado
# Vai perguntar a senha duas vezes — escolha algo com 16+ caracteres,
# misturando letras, números e símbolos.
```

Flags:
- `-t7z` → formato 7z
- `-mhe=on` → criptografa também os nomes dos arquivos (header encryption)
- `-p` → ativa proteção por senha

### Descriptografar (no destino)

```powershell
& "C:\Program Files\7-Zip\7z.exe" x saferoute-v2.7z
# Vai pedir a senha
```

Ou pelo Windows Explorer: clique direito → 7-Zip → Extract Here → digita a senha.

---

## Opção C — `age` (criptografia moderna, ferramenta unix-like)

Se você quer algo simples, scriptável e moderno (ed25519/X25519):

```powershell
# Instala via winget
winget install FiloSottile.age

# Empacota primeiro
Compress-Archive -Path saferoute-melhorado -DestinationPath saferoute-v2.zip

# Criptografa com senha
age --passphrase --output saferoute-v2.zip.age saferoute-v2.zip

# Pra abrir:
age --decrypt --output saferoute-v2.zip saferoute-v2.zip.age
```

Vantagem: **arquivo único `.age`**, formato auditável, padrão moderno.
Desvantagem: destinatário precisa ter `age` instalado.

---

## Opção D — GPG (compatível com qualquer SO, padrão de mercado)

```powershell
# Instala Gpg4win
winget install GnuPG.Gpg4win

# Empacota
Compress-Archive -Path saferoute-melhorado -DestinationPath saferoute-v2.zip

# Criptografa com senha simétrica AES-256
gpg --symmetric --cipher-algo AES256 saferoute-v2.zip
# Gera saferoute-v2.zip.gpg

# Pra abrir:
gpg --decrypt --output saferoute-v2.zip saferoute-v2.zip.gpg
```

---

## Boas práticas pra entregar o arquivo

1. **Senha NUNCA vai junto com o arquivo.** Mande por canal separado:
   - Arquivo: e-mail / Google Drive
   - Senha: WhatsApp / SMS / pessoalmente

2. **Senha forte:**
   - Mínimo 16 caracteres
   - Misture maiúsculas, minúsculas, números e símbolos
   - NÃO use palavras de dicionário sozinhas
   - Exemplo bom: `Saf3R0ut3!Puc-2026#Br`

3. **Hash de integridade** (pro destinatário verificar que não foi alterado):
   ```powershell
   Get-FileHash saferoute-v2.7z -Algorithm SHA256
   # Manda o hash junto. Destinatário roda o mesmo comando e compara.
   ```

4. **Inclua um README do pacote** explicando:
   - O que é
   - Como descriptografar
   - Como rodar (link pro README.md principal)
   - Quem entregou + data

---

## Tabela comparativa

| Método | Criptografia | Compatibilidade | Esforço |
|---|---|---|---|
| ZIP padrão | ❌ Fraca / inexistente | Universal | ⭐ |
| **7-Zip AES-256** | ✅ Forte | Windows/Mac/Linux com 7-Zip | ⭐⭐ |
| `age` | ✅ Moderna | Precisa instalar | ⭐⭐ |
| GPG | ✅ Padrão indústria | Universal (Gpg4win/GnuPG) | ⭐⭐⭐ |

**Recomendação para entrega acadêmica: 7-Zip com AES-256 + senha por canal separado.**
