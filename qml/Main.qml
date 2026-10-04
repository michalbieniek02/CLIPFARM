import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "." as Components

ApplicationWindow {
    id: window
    width: 1360; height: 900
    minimumWidth: 1100; minimumHeight: 780
    visible: true
    title: "Clipfarm — Studio klipów"
    color: "#ffffff"
    readonly property color canvasText: "#17202b"
    readonly property color canvasMuted: "#5f6b79"
    font.family: Theme.fontFamily
    property bool detailsOpen: false
    property bool captionEditOpen: false
    property string sourceTab: "Film"
    readonly property bool overlayActive: detailsOpen || preview.opened || captionEditOpen
    property var previousFocus: null
    onActiveFocusItemChanged: { if (!overlayActive && activeFocusItem && activeFocusItem.activeFocusOnTab && activeFocusItem.enabled) previousFocus = activeFocusItem; }
    onOverlayActiveChanged: {
        if (!overlayActive) Qt.callLater(function() { if (previousFocus && previousFocus.enabled) previousFocus.forceActiveFocus(); });
    }
    onDetailsOpenChanged: { if (detailsOpen) details.focusFirst(); else if (captionEditOpen) captionEditor.focusFirst(); else if (preview.opened) preview.focusFirst(); }
    onCaptionEditOpenChanged: { if (captionEditOpen) captionEditor.focusFirst(); }
    header: Rectangle {
        height: 76; color: Theme.sidebar
        RowLayout {
            enabled: !window.overlayActive
            anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 24; spacing: 14
            BrandMark { Layout.preferredWidth: 36; Layout.preferredHeight: 44 }
            Label { text: "CLIPFARM"; color: Theme.text; font.pixelSize: 24; font.weight: Font.Bold; font.letterSpacing: 1 }
            Rectangle { width: 1; height: 25; color: Theme.border; Layout.leftMargin: 8; Layout.rightMargin: 8 }
            Label { text: "Studio klipów"; color: Theme.muted; font.pixelSize: 13 }
            Item { Layout.fillWidth: true }
            TaskSpinner { running: backend.busy; Layout.preferredWidth: 24; Layout.preferredHeight: 24 }
            UpdateNotice { Layout.preferredWidth: updates.installing ? 300 : 44; visible: updates.available || updates.installing }
            PrimaryButton { objectName: "editCaptionsButton"; text: "Edytuj napisy"; visible: !updates.installing; enabled: backend.transcriptReady && !backend.busy; onClicked: window.captionEditOpen = true }
            PrimaryButton { text: "Otwórz projekt"; visible: !updates.installing; enabled: !backend.busy; onClicked: backend.openProject() }
            PrimaryButton { text: "Zapisz projekt"; visible: !updates.installing; enabled: !!backend.videoPath && !backend.busy; onClicked: { window.contentItem.forceActiveFocus(); backend.saveProject(); } }
        }
    }
    RowLayout {
        enabled: !window.overlayActive && !updates.installing
        anchors.fill: parent; spacing: 0
        Sidebar { Layout.preferredWidth: 296; Layout.fillHeight: true }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 24; spacing: 16
            ColumnLayout { Layout.fillWidth: true; spacing: 6; Label { Layout.fillWidth: true; text: window.sourceTab === "Film" ? "Z filmu. W najlepsze momenty." : "Z linku prosto do klipów."; color: window.canvasText; font.pixelSize: 30; font.weight: Font.DemiBold; wrapMode: Text.WordWrap } Label { Layout.fillWidth: true; text: window.sourceTab === "Film" ? "Dodaj materiał, znajdź fragmenty i przygotuj klipy do publikacji." : "Pobierz materiał z Kicka, Twitcha, YouTube lub X."; color: window.canvasMuted; font.pixelSize: 13; wrapMode: Text.WordWrap } }
            SegmentTabs { objectName: "sourceTabs"; Layout.preferredWidth: 290; options: ["Film", "Pobierz VOD"]; value: window.sourceTab; onChosen: value => window.sourceTab = value }
            VideoCard { Layout.fillWidth: true; visible: window.sourceTab === "Film" }
            VodCard { Layout.fillWidth: true; visible: window.sourceTab === "Pobierz VOD" }
            RowLayout {
                visible: window.sourceTab === "Film"
                Layout.fillWidth: true
                Label { text: "Twoje klipy"; color: window.canvasText; font.pixelSize: 21; font.weight: Font.DemiBold }
                Label { text: backend.clipCount ? "· " + backend.clipCount : ""; color: window.canvasMuted; font.pixelSize: 16 }
                Item { Layout.fillWidth: true }
                PrimaryButton { text: "Przerwij"; visible: backend.busy; onClicked: backend.cancelTask() }
                PrimaryButton { text: backend.settings.mode === "Film · minuty" ? "Podziel cały film" : "Znajdź fragmenty"; primary: true; enabled: !!backend.videoPath && !backend.busy; onClicked: { window.contentItem.forceActiveFocus(); backend.analyze(); } }
            }
            Item {
                id: results; Layout.fillWidth: true; Layout.fillHeight: true; visible: window.sourceTab === "Film"
                state: backend.busy && backend.clipCount === 0 ? "loading" : backend.clipCount > 0 ? "clips" : "empty"
                Item {
                    id: empty; anchors.fill: parent; visible: opacity > 0
                    transform: Translate { y: results.state === "empty" ? 0 : 10; Behavior on y { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } } }
                    ColumnLayout { anchors.centerIn: parent; width: Math.min(parent.width - 48, 440); spacing: 14; Image { visible: results.height >= 220; source: "../assets/clipfarm-mark.png"; Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 54; Layout.preferredHeight: 70; fillMode: Image.PreserveAspectFit; opacity: 0.8 } Label { text: "Najlepsze momenty są jeszcze przed Tobą"; color: window.canvasText; font.pixelSize: 20; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true } Label { text: "Po analizie zobaczysz tu klipy. Każdy możesz obejrzeć, poprawić i wyeksportować."; color: window.canvasMuted; font.pixelSize: 13; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true } }
                }
                Item {
                    id: loading; anchors.fill: parent; opacity: 0; visible: opacity > 0
                    transform: Translate { y: results.state === "loading" ? 0 : 10; Behavior on y { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } } }
                    ColumnLayout { anchors.centerIn: parent; spacing: 18; TaskSpinner { Layout.preferredWidth: 40; Layout.preferredHeight: 40; Layout.alignment: Qt.AlignHCenter; running: backend.busy } Label { text: "Przygotowujemy Twoje klipy…"; color: window.canvasText; font.pixelSize: 20 } Label { text: "Możesz śledzić postęp w szczegółach zadania."; color: window.canvasMuted; font.pixelSize: 12 } }
                }
                ListView {
                    id: list; anchors.fill: parent; clip: true; opacity: 0; visible: opacity > 0; spacing: 12
                    model: backend.clipModel
                    delegate: ClipCard { width: ListView.view.width }
                    ScrollBar.vertical: ScrollBar { }
                    remove: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.fast } }
                    displaced: Transition { NumberAnimation { properties: "y"; duration: Theme.normal; easing.type: Easing.OutCubic } }
                }
                states: [State { name: "empty"; PropertyChanges { target: empty; opacity: 1 } PropertyChanges { target: loading; opacity: 0 } PropertyChanges { target: list; opacity: 0 } }, State { name: "loading"; PropertyChanges { target: empty; opacity: 0 } PropertyChanges { target: loading; opacity: 1 } PropertyChanges { target: list; opacity: 0 } }, State { name: "clips"; PropertyChanges { target: empty; opacity: 0 } PropertyChanges { target: loading; opacity: 0 } PropertyChanges { target: list; opacity: 1 } }]
                transitions: Transition { NumberAnimation { property: "opacity"; duration: Theme.normal; easing.type: Easing.OutCubic } }
                Rectangle { anchors.fill: parent; visible: backend.busy && backend.clipCount > 0; color: "#99121820"; radius: Theme.radius; TaskSpinner { anchors.centerIn: parent; width: 40; height: 40; running: parent.visible } }
            }
            Item { Layout.fillWidth: true; Layout.fillHeight: true; visible: window.sourceTab === "Pobierz VOD" }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: backend.errorMessage ? 54 : 0; visible: height > 0; color: "#422c30"; radius: Theme.controlRadius; clip: true
                RowLayout { anchors.fill: parent; anchors.margins: 10; Label { Layout.fillWidth: true; text: "Wystąpił błąd podczas zadania."; color: Theme.text; font.pixelSize: 13 } PrimaryButton { text: "Szczegóły"; implicitHeight: 32; onClicked: window.detailsOpen = true } PrimaryButton { text: "Zamknij"; implicitHeight: 32; onClicked: backend.dismissError() } }
            }
            RowLayout {
                Layout.fillWidth: true
                visible: window.sourceTab === "Film"
                Label { text: "Wybrano " + backend.selectedCount + " z " + backend.clipCount; color: window.canvasMuted; font.pixelSize: 12 }
                Item { Layout.fillWidth: true }
                PrimaryButton { text: "Folder eksportu"; enabled: !backend.busy; onClicked: backend.openDestination() }
                PrimaryButton { text: "Eksportuj klipy"; primary: true; enabled: backend.selectedCount > 0 && !backend.busy; onClicked: { window.contentItem.forceActiveFocus(); backend.exportClips(); } }
            }
            RowLayout {
                Layout.fillWidth: true
                Label { Layout.fillWidth: true; text: backend.status; color: window.canvasMuted; font.pixelSize: 11; elide: Text.ElideRight }
                Label { visible: backend.busy && backend.progress >= 0; text: Math.round(backend.progress * 100) + "%"; color: window.canvasMuted; font.pixelSize: 11 }
                PrimaryButton { text: "Szczegóły"; implicitHeight: 30; font.pixelSize: 11; onClicked: window.detailsOpen = true }
            }
            Components.ProgressBar { Layout.fillWidth: true; value: backend.progress; busy: backend.busy }
        }
        SettingsPreview { Layout.preferredWidth: 248; Layout.fillHeight: true; Layout.topMargin: 24; Layout.bottomMargin: 24; Layout.rightMargin: 24 }
    }
    DropArea { anchors.fill: parent; z: -1; enabled: !backend.busy && !updates.installing && !window.overlayActive; onDropped: event => { if (event.hasUrls) { backend.dropFiles(event.urls); event.acceptProposedAction(); } } }
    Rectangle { anchors.fill: parent; z: 10; color: "#66000000"; opacity: window.overlayActive ? 1 : 0; visible: opacity > 0; Behavior on opacity { NumberAnimation { duration: Theme.fast } } MouseArea { anchors.fill: parent; onClicked: { if (window.detailsOpen) window.detailsOpen = false; else if (window.captionEditOpen) window.captionEditOpen = false; else { preview.opened = false; backend.closePreview(); } } } }
    VideoPreview { id: preview; enabled: opened && !window.detailsOpen }
    CaptionEditor { id: captionEditor; opened: window.captionEditOpen; enabled: opened && !window.detailsOpen; onCloseRequested: window.captionEditOpen = false }
    DetailsPanel { id: details; opened: window.detailsOpen; onCloseRequested: window.detailsOpen = false }
    Connections { target: backend; function onErrorOccurred(text) { window.detailsOpen = true } }
    Shortcut { sequence: "Ctrl+O"; enabled: !backend.busy && !updates.installing && !window.overlayActive; onActivated: backend.openProject() }
    Shortcut { sequence: "Ctrl+S"; enabled: !backend.busy && !updates.installing && !!backend.videoPath && !window.overlayActive; onActivated: { window.contentItem.forceActiveFocus(); backend.saveProject(); } }
    Shortcut { sequence: "Escape"; onActivated: { if (window.detailsOpen) window.detailsOpen = false; else if (window.captionEditOpen) window.captionEditOpen = false; else if (preview.opened) { preview.opened = false; backend.closePreview(); } else if (backend.busy) backend.cancelTask(); } }
    onClosing: function(close) { close.accepted = backend.requestClose() }
}
