import QtQuick
Rectangle {
    id: root
    property real value: 0
    property bool busy: false
    implicitHeight: 4; radius: 2; color: Theme.raised; clip: true
    Rectangle {
        id: bar
        height: parent.height; radius: 2; color: Theme.accent
        width: root.value < 0 ? root.width * 0.24 : root.width * Math.max(0, Math.min(1, root.value))
        Behavior on width { NumberAnimation { duration: Theme.normal; easing.type: Easing.OutCubic } }
        NumberAnimation on x { from: -bar.width; to: root.width; duration: 1300; loops: Animation.Infinite; running: root.busy && root.value < 0 && backend.animationsEnabled }
        Rectangle {
            width: 70; height: parent.height; opacity: 0.35
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "transparent" } GradientStop { position: 0.5; color: "white" } GradientStop { position: 1; color: "transparent" } }
            NumberAnimation on x { from: -70; to: bar.width; duration: 1200; loops: Animation.Infinite; running: root.busy && backend.animationsEnabled }
        }
    }
    onValueChanged: { if (value >= 0) bar.x = 0 }
    onBusyChanged: { if (!busy) bar.x = 0 }
}
