"""One box in the decision graph: a test or an action, drawn with its live value."""
from __future__ import annotations

from vispy.scene import visuals

from ..policy.decision_node import DecisionNode
from . import palette

BAR_HEIGHT: float = 5.0


class NodeBox:
    """A rounded box holding a label, an answer, and a bar showing how close the
    condition is to firing.

    The bar is the part that matters. A row of labels is a diagram of the policy; a
    bar creeping toward its threshold is the policy about to make up its mind, and
    you can see it coming several seconds out.
    """

    def __init__(self, parent: object) -> None:
        self.frame = visuals.Rectangle(center=(0.0, 0.0), width=10.0, height=10.0,
                                       radius=4.0, color=palette.NODE_FILL,
                                       border_color=palette.NODE_EDGE,
                                       border_width=1, parent=parent)
        self.label = visuals.Text("", parent=parent, anchor_x="left", anchor_y="center",
                                  color=palette.HUD, font_size=9)
        self.answer = visuals.Text("", parent=parent, anchor_x="right", anchor_y="center",
                                   color=palette.DIM, font_size=8.5, bold=True)
        self.detail = visuals.Text("", parent=parent, anchor_x="left", anchor_y="center",
                                   color=palette.DIM, font_size=7.5)
        # The bar is not a visual of its own. In a shown window every property set on
        # a Rectangle regenerates its geometry and forces a synchronous repaint, and
        # ten bars moving every frame cost four hundred milliseconds a paint. The box
        # only records where its bar should be; the graph draws all of them at once.
        self.bar: tuple[float, float, float, float, bool] | None = None
        self._cache: tuple = ()
        self.set_visible(False)

    def set_visible(self, visible: bool) -> None:
        for v in (self.frame, self.label, self.answer, self.detail):
            v.visible = visible
        if not visible:
            self.bar = None

    def place(self, x: float, y: float, width: float, height: float) -> None:
        if (x, y, width, height) == (getattr(self, "x", None), getattr(self, "y", None),
                                     getattr(self, "width", None), getattr(self, "height", None)):
            return                # unchanged: setting the rectangle again would regenerate
                                  # its geometry and force a repaint, for nothing
        self._cache = ()          # moved: text positions must be laid out again
        self.x, self.y, self.width, self.height = x, y, width, height
        self.frame.center = (x + width / 2, y + height / 2)
        self.frame.width = width
        self.frame.height = height

    def show(self, node: DecisionNode) -> None:
        # Two separate concerns. Assigning to a vispy Text rebuilds its glyph atlas,
        # so strings and styling are only touched when they actually change -- while
        # the bar geometry, which is cheap, is updated every frame. Keying the whole
        # method on the bar fill meant every label in the graph was rebuilt on every
        # frame, and the recorder fell from 14 fps to 3.
        style_key = (node.label, node.answer, node.detail, node.active,
                     node.fired, node.kind)
        restyle = style_key != self._cache
        self._cache = style_key
        if restyle:
            self.set_visible(True)
            x, y, w, h = self.x, self.y, self.width, self.height
            pad = 10.0

            if node.kind == "action":
                self.frame.color = palette.NODE_ACTION_FILL if node.fired else palette.NODE_FILL
                self.frame.border_color = palette.NODE_ACTION_EDGE
                self.label.color = palette.TREE_LIVE
                self.label.font_size = 9.5
                self.label.bold = True
            elif node.kind == "sub":
                self.frame.color = palette.NODE_SUB_FILL
                self.frame.border_color = palette.NODE_SUB_EDGE
                self.label.color = palette.HUD if node.active else palette.DIM
                self.label.font_size = 8
                self.label.bold = False
            else:
                fired = node.fired
                self.frame.color = palette.NODE_TEST_HOT if fired else palette.NODE_FILL
                self.frame.border_color = palette.NODE_EDGE_HOT if fired else palette.NODE_EDGE
                self.label.color = palette.TITLE if node.active else palette.DIM
                self.label.font_size = 9
                self.label.bold = False

            has_bar = node.fill >= 0.0
            # Explicit rows. Deriving these from the box height packed the detail line
            # into the bar and, in the short sub boxes, on top of the label itself.
            if node.kind == "sub":
                label_y = y + 11.0
                detail_text, detail_y = "", 0.0
                right_text, right_y = node.detail, y + 11.0
                bar_y = y + 24.0
            elif node.kind == "action":
                label_y = y + h / 2
                detail_text, detail_y = "", 0.0
                right_text, right_y = node.answer, y + h / 2
                bar_y = y + h - 7.0
            else:
                label_y = y + 15.0
                detail_text, detail_y = node.detail, y + 31.0
                right_text, right_y = node.answer, y + 15.0
                bar_y = y + 43.0

            self.label.text = node.label
            self.label.pos = (x + pad, label_y)

            self.answer.text = right_text
            self.answer.pos = (x + w - pad, right_y)
            if node.answer == "yes":
                self.answer.color = palette.BANNER
            elif node.answer == "no":
                self.answer.color = palette.DIM
            else:
                self.answer.color = palette.DIM

            if detail_text:
                self.detail.visible = True
                self.detail.text = detail_text
                self.detail.pos = (x + pad, detail_y)
            else:
                self.detail.visible = False

        x, y, w, h = self.x, self.y, self.width, self.height
        pad = 10.0
        has_bar = node.fill >= 0.0
        if node.kind == "sub":
            bar_y = y + 24.0
        elif node.kind == "action":
            bar_y = y + h - 7.0
        else:
            bar_y = y + 43.0

        if has_bar:
            bar_w = w - pad * 2
            fill = min(max(node.fill, 0.0), 1.0)
            self.bar = (x + pad, bar_y, bar_w, bar_w * fill, fill >= 0.999)
        else:
            self.bar = None
