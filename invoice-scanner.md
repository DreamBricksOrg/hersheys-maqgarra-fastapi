# Plan: Invoice Scanner Feature

## Overview
Implement a camera scanner feature using `jscanify` to capture and process invoice images (notas fiscais). The interface will display a camera feed, draw a dynamic boundary over the document, allow capturing, and present a modal to confirm the image quality. The final captured image will be sent to the backend to be saved as a static file.

## Project Type
**WEB** (FastAPI backend with Vanilla JS/CSS frontend)

## Success Criteria
1. The camera feed opens within the `.camera-container`.
2. The rear camera is selected by default.
3. A button allows swapping cameras.
4. `jscanify` draws a dynamic contour over detected documents.
5. Capturing crops and applies color enhancement (like CamScanner) using `jscanify`.
6. A centered modal with a darkened background asks if the photo is good.
7. Upon confirmation, the image is uploaded to a FastAPI endpoint and saved locally as a static file.

## Tech Stack
- **Frontend:** HTML5, CSS3, Vanilla JS.
- **Library:** `jscanify` (OpenCV wrapper for document detection and perspective transform).
- **Backend:** FastAPI for receiving the base64/blob image and saving it to disk.

## File Structure
```
src/
├── api/
│   └── uploads.py (NOVO) - Rota de upload de imagem
├── static/
│   ├── templates/
│   │   └── read-camera.html - Adicionar `<video>`, `<canvas>`, botões e modal
│   ├── assets/
│   │   ├── css/
│   │   │   └── read-camera.css - Estilos da modal (fundo escuro) e botões centrados
│   │   └── js/
│   │       └── read-camera.js - Lógica da câmera, jscanify e requisição pro backend
│   └── uploads/ - Pasta de destino para as imagens
```

## Task Breakdown

### [ ] 1. Implement Backend Image Upload Endpoint
**Agent:** `backend-specialist`
**Skill:** `api-patterns`
**Priority:** P1
**Dependencies:** None
- **INPUT:** Imagem base64 ou blob (multpart).
- **OUTPUT:** Endpoint FastAPI (`POST /api/upload`) que verifica a extensão, salva o arquivo na pasta `src/static/uploads/` e retorna o caminho. Adicionar o roteador no `main.py`.
- **VERIFY:** Enviar um payload de teste e checar se o arquivo aparece no disco.

### [ ] 2. Update HTML & CSS for Camera Interface and Modal
**Agent:** `frontend-specialist`
**Skill:** `frontend-design`
**Priority:** P2
**Dependencies:** None
- **INPUT:** `read-camera.html` e `read-camera.css`.
- **OUTPUT:** 
  - Estrutura HTML do `<video>` escondido, e um `<canvas>` de exibição (onde o jscanify vai desenhar os contornos).
  - Botão direito centralizado para capturar.
  - Botão no topo ou lado para inverter a câmera.
  - Estrutura da Modal invisível por padrão.
  - CSS implementando o fundo meio escuro da modal (`rgba(0,0,0,0.7)`).
- **VERIFY:** Abrir o HTML e testar a visualização da modal mudando suas classes.

### [ ] 3. Implement Camera Logic and JScanify Integration
**Agent:** `frontend-specialist`
**Skill:** `frontend-design`
**Priority:** P2
**Dependencies:** Task 2
- **INPUT:** Script `read-camera.js`.
- **OUTPUT:**
  - Importar OpenCV.js e jscanify (via CDN no HTML).
  - Acessar `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })`.
  - Lógica para trocar a câmera.
  - Loop de renderização com `requestAnimationFrame` que puxa do `<video>`, usa `scanner.highlightPaper()` para desenhar o molde da nota na imagem, e joga no `<canvas>` exibido na tela.
- **VERIFY:** Abrir a página (via celular ou DevTools) e verificar se o retângulo vermelho dinâmico aparece ao focar num documento.

### [ ] 4. Implement Capture, Image Enhancement, and API Integration
**Agent:** `frontend-specialist`
**Skill:** `frontend-design`
**Priority:** P2
**Dependencies:** Task 1, 2, 3
- **INPUT:** Canvas com imagem da nota e endpoint backend.
- **OUTPUT:**
  - Lógica do botão capturar: invocar `scanner.extractPaper()`.
  - Aplicar filtro de realce (jscanify text enhancement ou filtro opencv) na imagem extraída.
  - Pausar o feed da câmera e abrir a Modal com o resultado final (ajustado).
  - Ao clicar em "Salvar" na Modal, enviar a foto resultante via `fetch` POST para a API do backend. Após sucesso, emitir alerta ou fechar a aba atual.
- **VERIFY:** Bater a foto, visualizar a imagem realçada na Modal, confirmar, e certificar que a resposta `200 OK` retornou.

## ✅ PHASE X: Verification
- [ ] Run `lint_runner.py` (se aplicável ao código python).
- [ ] Run `security_scan.py` para validar endpoints adicionados.
- [ ] QA Visual (responsividade da câmera e proporções do Canvas).
- [ ] E2E / Teste manual de captura enviando arquivo ao backend.
