# MaineMed — instalar no Mac (passo a passo)

## 1) Baixar

Abra este link no Safari ou Chrome — o download começa sozinho:

**https://github.com/horstmr/mainemed/releases/download/mainemed-v1.0.0/MaineMed-macOS-arm64.zip**

## 2) Instalar

1. Vá em **Downloads** e dê dois cliques no arquivo baixado. Vai aparecer o **MaineMed**.
2. Arraste o **MaineMed** para a pasta **Aplicativos**.

## 3) Abrir pela primeira vez (atenção neste passo!)

O aviso que vai aparecer é normal: o programa é feito sob encomenda, não
passou pela loja da Apple — não é vírus. Só precisa fazer isso na primeira
vez; depois abre com dois cliques normalmente.

**No macOS Sequoia (15):**
1. Dê dois cliques no MaineMed → vai aparecer um aviso dizendo que não foi
   possível abrir → clique em **Concluído/OK**.
2. Abra **Ajustes do Sistema → Privacidade e Segurança**, role até o final:
   vai ter uma linha sobre o MaineMed → clique em **Abrir Assim Mesmo** e
   confirme com sua senha.

**No macOS 13/14 (Ventura/Sonoma):** clique no MaineMed com o **botão
direito → Abrir** → no aviso, clique em **Abrir** de novo.

## 4) Permitir o microfone

Na primeira gravação o Mac vai perguntar se o MaineMed pode usar o
microfone → clique em **Permitir**. (Se negar sem querer: Ajustes do Sistema
→ Privacidade e Segurança → Microfone → ligar o MaineMed.)

## 5) Colar a chave

Na primeira abertura ele pede uma "chave". Peça a chave para mim, cole no
campo e clique em **Salvar e começar**.

## 6) Usar

1. Escreva o nome do paciente.
2. Clique no botão **Gravar consulta**. Clique de novo para parar.
   - Na **primeira** gravação ele baixa o que precisa (≈1,6 GB) — demora
     alguns minutos e **precisa de internet**. Nas próximas é rápido.
3. Clique em **Gerar prontuário**. Dá para editar o texto, **Copiar** ou
   exportar em **Word/PDF**.

A transcrição do áudio acontece **só no seu Mac** — a gravação não é enviada
para lugar nenhum.

## Se der errado

- **"O aplicativo está danificado"** ou não abre de jeito nenhum → abra o
  aplicativo **Terminal**, cole a linha abaixo e aperte Enter, depois tente
  abrir de novo:

  ```
  xattr -cr /Applications/MaineMed.app
  ```

- A transcrição veio **vazia** → confira se a barra "nível do microfone" se
  mexe durante a gravação; se não mexer, é permissão do microfone (passo 4).
- Qualquer outro erro → tire um print da tela e me manda.
