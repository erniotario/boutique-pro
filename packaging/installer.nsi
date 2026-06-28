; Script NSIS pour l'installeur Windows de BoutiquePro.
;
; Prerequis :
;   - Avoir construit l'application avec packaging/build_exe.sh (PyInstaller,
;     mode --onedir), ce qui produit le dossier dist/BoutiquePro/ contenant
;     BoutiquePro.exe et ses dependances.
;   - NSIS (https://nsis.sourceforge.io/) installe sur la machine de build.
;
; Pour generer l'installeur (depuis la racine du depot, sous Windows) :
;   makensis packaging\installer.nsi
;
; Le fichier de sortie sera : packaging\BoutiquePro-Setup.exe

!define APP_NAME "BoutiquePro"
!define APP_PUBLISHER "BoutiquePro"
!define APP_VERSION "1.0.0"
!define APP_EXE "BoutiquePro.exe"

; Dossier produit par PyInstaller (relatif a ce script .nsi)
!define DIST_DIR "..\dist\BoutiquePro"

Name "${APP_NAME}"
OutFile "BoutiquePro-Setup.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin

!include "MUI2.nsh"

!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "French"

Section "BoutiquePro (obligatoire)" SEC01
    SectionIn RO
    SetOutPath "$INSTDIR"

    ; Copie recursive de tout le contenu produit par PyInstaller (onedir)
    File /r "${DIST_DIR}\*.*"

    ; Raccourcis menu Demarrer
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Desinstaller ${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"

    ; Raccourci bureau (optionnel mais pratique)
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"

    ; Informations de desinstallation dans le registre
    WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "DisplayVersion" "${APP_VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
        "NoRepair" 1

    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"

    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Desinstaller ${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd
