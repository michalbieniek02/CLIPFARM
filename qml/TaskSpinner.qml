import QtQuick
Item {
    id: root
    property bool running: true
    implicitWidth: 24; implicitHeight: 24
    opacity: running ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: Theme.fast } }
    Canvas { anchors.fill: parent; onPaint: { let c = getContext("2d"); c.clearRect(0,0,width,height); c.strokeStyle = Theme.accentHover; c.lineWidth = 2.5; c.lineCap = "round"; c.beginPath(); c.arc(width/2,height/2,width/2-3,0,Math.PI*1.45); c.stroke(); } }
    NumberAnimation on rotation { from: 0; to: 360; duration: 950; loops: Animation.Infinite; running: root.running && backend.animationsEnabled }
}
