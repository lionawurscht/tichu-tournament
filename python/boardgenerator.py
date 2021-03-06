"""Generates Tichu boards and renders them to pdf.
"""

import json
import math
import random
import os

from svglib.svglib import svg2rlg
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


class _Color:
  """Type representing a Tichu suit (stars, falchions, pagodas or jades).

  Attributes:
    name: String. The color's name, as it appears in board images.
    value: Integer. The color's ranking (1-4) for sorting purposes.
    rgbcolor: Tuple of three integers. RGB color that this color is rendered
        in.
    offset: Tuple of two integers. Represents X and Y offset relative to the
        upper left corner of rendering card names in hand overviews, in
        pixels.
  """
  def __init__(self, name, symbol, value, rgbcolor, offset):
    self.name = name
    self.value = value
    self.rgbcolor = rgbcolor
    self.offset = offset
    self._symbolName = symbol
    self._symbol = None

  def GetSymbol(self):
    """Returns this color's symbol image data.

    Lazily created and cached across calls.
    """
    if not self._symbol and self._symbolName:
      path = os.path.join(os.path.split(__file__)[0], "icons/%s.svg" % self._symbolName)
      self._symbol = svg2rlg(path)
      self._symbol.scale(.18, .18)

    return self._symbol

class _Card:
  """Representation of a single card within a board.

  Attributes:
    color: Color object representing the cards suit.
    shortName: String for rendering the card within hand overviews.
    order: Integer unique to each card by which cards can be sorted.
    id: String name by which card images are identified.
  """

  _CARDS = []

  def __init__(self, color, shortName, order, id):
    self.color = color
    self.shortName = shortName
    self.order = order
    self.id = id

  def ToJson(self):
    """Returns this card's JSON representation.
    """
    return self.order

  @classmethod
  def FromJson(cls, order):
    """Returns a card given the cards order.

    Arguments:
      order: Integer uniquely identifying this card's order.
    """
    return cls.AllCards()[order]

  @classmethod
  def AllCards(cls):
    """Returns a list of all cards in Tichu, sorted by their order.

    The cards are cached across calls but this method will always return a new
    list when called.
    """
    if not cls._CARDS:
      cards = []
      for color in _COLORS:
        offset = color.value + 2
        for i in range(2, 10):
          cards.append(_Card(color, i, 4 * (i - 2) + offset, color.name + str(i)))
        cards.append(_Card(color, "T", 4 * 8 + offset, color.name + "10"))
        cards.append(_Card(color, "J", 4 * 9 + offset, color.name + "B"))
        cards.append(_Card(color, "Q", 4 * 10 + offset, color.name + "D"))
        cards.append(_Card(color, "K", 4 * 11 + offset, color.name + "K"))
        cards.append(_Card(color, "A", 4 * 12 + offset, color.name + "As"))
      cards.append(_Card(_SPECIAL_COLOR, "H", 0, "Hund"))
      cards.append(_Card(_SPECIAL_COLOR, "1", 1, "MJ"))
      cards.append(_Card(_SPECIAL_COLOR, "P", 54, "Phoenix"))
      cards.append(_Card(_SPECIAL_COLOR, "Dr", 55, "Drache"))
      cls._CARDS = sorted(cards, key=lambda x: x.order)

    return cls._CARDS[:]


class Position:
  """A position on boards (north, south, east, west).

  Not specific to any board instance.

  Attributes:
    name: String position name, used for rendering.
    id: Integer multiplier by which cards are matched to positions within
        boards. Unique to each position.
    firstEightOffset: Tuple of two integers. Represents X and Y offset from
        top left by which this position's first eight card icons are drawn,
        in pixels.
    fullOffset: Tuple of two integers. Represents X and Y offset from top
        left by which this position's full hand description is rendered, in
        pixels.
    labelOffset: Tuple of two integers. Represents X and Y offset from top
        left by which this position's label is placed in the hand overview's
        central box, in pixels.
  """
  def __init__(self, name, id, firstEightOffset, fullOffset, labelOffset):
    self.name = name
    self.id = id
    self.firstEightOffset = firstEightOffset
    self.fullOffset = fullOffset
    self.labelOffset = labelOffset


# General constants used in rendering hands.
_PAGE_WIDTH = LETTER[0]
_LEFT_MARGIN = 0
_TOP_MARGIN = 0
_IMG_WIDTH = 40
_IMG_HEIGHT = 60
_IMG_MARGIN = 2
_COLOR_ID_WIDTH = 14
_CARD_ID_HEIGHT = 11


# Constants used in rendering the first eight cards of each hand.
_FIRST_MARGIN = 40
_FIRST_LABEL_HEIGHT = 11
_FIRST_LABEL_MARGIN = 4
_FIRST_WIDTH = 4 * _IMG_WIDTH + 3 * _IMG_MARGIN
_FIRST_HEIGHT = 2 * _IMG_HEIGHT + _FIRST_LABEL_HEIGHT + _IMG_MARGIN + _FIRST_LABEL_MARGIN
_FIRST_REMAINING_WIDTH = _PAGE_WIDTH - (2 * _FIRST_WIDTH + _FIRST_MARGIN + 2 * _LEFT_MARGIN)
_FIRST_1_X = _FIRST_REMAINING_WIDTH / 2
_FIRST_1_Y = 70
_FIRST_2_X = _FIRST_1_X + _FIRST_WIDTH + _FIRST_MARGIN
_FIRST_2_Y = _FIRST_HEIGHT + _FIRST_MARGIN + _FIRST_1_Y


# Constants used in rendering the full hand overview for each hand.
_FULL_MARGIN = 20
_FULL_WIDTH = 90
_FULL_HEIGHT = 5 * _CARD_ID_HEIGHT
_FULL_REMAINING_WIDTH = _PAGE_WIDTH - (3*_FULL_WIDTH + 2*_FULL_MARGIN + 2*_LEFT_MARGIN)
_FULL_1_X = _FULL_REMAINING_WIDTH/2
_FULL_2_X = _FULL_1_X + _FULL_WIDTH + _FULL_MARGIN
_FULL_3_X = _FULL_2_X + _FULL_WIDTH + _FULL_MARGIN
_FULL_1_Y = 2*_FIRST_HEIGHT + _FIRST_MARGIN + 150
_FULL_2_Y = _FULL_1_Y + _FULL_HEIGHT + _FULL_MARGIN
_FULL_3_Y = _FULL_2_Y + _FULL_HEIGHT + _FULL_MARGIN

# Constants used in rendering the center of full hand overviews.
_CENTER_LABEL_MARGIN = 3
_CENTER_X = _FULL_2_X - _FULL_MARGIN/2
_CENTER_Y = _FULL_2_Y - _FULL_MARGIN/2
_CENTER_WIDTH = _FULL_WIDTH + _FULL_MARGIN
_CENTER_HEIGHT = _FULL_HEIGHT + _FULL_MARGIN


# Position constants.
_NORTH = Position(
  "North",
  0,
  (_FIRST_1_X, _FIRST_1_Y),
  (_FULL_2_X, _FULL_1_Y),
  (_CENTER_X + _CENTER_WIDTH / 2, _CENTER_Y + _CENTER_LABEL_MARGIN)
)
_EAST = Position(
  "East",
  1,
  (_FIRST_2_X, _FIRST_1_Y),
  (_FULL_3_X, _FULL_2_Y),
  (_CENTER_X + _CENTER_WIDTH - _CENTER_LABEL_MARGIN, _CENTER_Y + _CENTER_HEIGHT / 2)
)
_SOUTH = Position(
  "South",
  2,
  (_FIRST_1_X, _FIRST_2_Y),
  (_FULL_2_X, _FULL_3_Y),
  (_CENTER_X + _CENTER_WIDTH / 2, _CENTER_Y + _CENTER_HEIGHT - _CENTER_LABEL_MARGIN)
)
_WEST = Position(
  "West",
  3,
  (_FIRST_2_X, _FIRST_2_Y),
  (_FULL_1_X, _FULL_2_Y),
  (_CENTER_X + _CENTER_LABEL_MARGIN, _CENTER_Y + _CENTER_HEIGHT / 2)
)
_POSITIONS = [_NORTH, _EAST, _SOUTH, _WEST]

# Color constants.
_SPECIAL_COLOR = _Color("special", None, -1, (0, 0, 0), (0, 5 * _CARD_ID_HEIGHT))
_COLORS = [
  _Color("blau", "pagoda", 0, (37, 143, 209), (0, _CARD_ID_HEIGHT)),
  _Color("gruen", "jade", 1, (45, 117, 56), (0, 2 * _CARD_ID_HEIGHT)),
  _Color("schw", "falchion", 2, (0, 0, 0), (0, 3 * _CARD_ID_HEIGHT)),
  _Color("rot", "star", 3, (237, 69, 59), (0, 4 * _CARD_ID_HEIGHT)),
]


class Board:
  """A board within a tournament.

  Attributes:
    id: Integer. Unique ID by which this board can be identified within the
        tournament.
    cards: List of card objects, sorted according to position: The first
        eight entries represent the first eight cards of the position with
        ID 0, the next six cards the remainder of that position's hand. Then
        follow the first eight cards of position with ID 1 and so on.
  """
  def __init__(self, id, cards = None):
    """Creates a board with the given ID.

    Arguments:
      cards: Optional. If not specified a new set of cards will be randomly
          generated.
    """
    self.id = id
    if not cards:
      cards = _Card.AllCards()
      random.shuffle(cards)
    self.cards = cards

  def GetFull(self, position):
    """Returns the full hand for the given position.

    Returns: A list of card objects, sorted by reverse order (thus, with the
        highest ordered cards first).
    """
    return sorted(self.cards[position.id*14:(position.id+1)*14], key=lambda x: -x.order)

  def GetFirstEight(self, position):
    """Returns the first eight cards for the given position.

    Returns: A list of card objects, sorted by reverse order (thus, with the
        highest ordered cards first).
    """
    return sorted(self.cards[position.id*14:(position.id+1)*14-6], key=lambda x: -x.order)

  def ToJson(self):
    """Returns a JSON representation of this board.

    The returned representation can be deserialized by this type's FromJson
    method.
    """
    cards = []
    for card in self.cards:
      cards.append(card.ToJson())

    return json.dumps({'id': self.id, 'cards': cards})

  @classmethod
  def FromJson(cls, modelBoard):
    """Returns a board object created from the passed JSON representation.

    The JSON representation must have been created by the ToJson method of this
    type.
    """
    decoded = json.loads(modelBoard.board)
    return cls(id=modelBoard.board_number, cards=[_Card.FromJson(c) for c in decoded['cards']])


def _Offsets(*args):
  """Combines any number of given offsets, relative to the upper left corner.

  By default reportlab will render offsets from the bottom left which is
  unintuitive. This function assumes its inputs are relative to the *upper*
  left but returns a value compatible with reportlab.

  Arguments:
    *args: Any number of tuples of two integers, representing the X and Y
        offsets respectively, in pixels.
  """
  x = 0
  y = 0
  for arg in args:
    x += arg[0]
    y += arg[1]
  return (x, LETTER[1] - y)


class _BoardRenderer:
  """Renderer that converts board objects into PDF files.

  A board is represented by a single page with four "first eight" sections,
  containing the name of the relevant position, the board number and the first
  eight cards as icons. The page also contains an overview of the entire hand.

  Attributes:
    canvas: reportlab canvas object to draw on.
    board: A board object to render.
  """

  def __init__(self, board, canvas):
    self.canvas = canvas
    self.board = board

  def Render(self):
    """Renders the board this renderer was initialized with on a new page.

    Adds to the current page on the given canvas and ends that page before
    returning.
    """
    for position in _POSITIONS:
      self._RenderFirstEight(position)
      self._RenderFull(position)

    self._RenderCenter()
    self.canvas.showPage()

  def _RenderFirstEight(self, position):
    cards = self.board.GetFirstEight(position)

    offset = _Offsets(position.firstEightOffset, (_FIRST_WIDTH / 2, _FIRST_LABEL_HEIGHT))
    self.canvas.setFont('Helvetica-Bold', 10)
    self.canvas.setFillColorRGB(0, 0, 0)
    self.canvas.drawCentredString(
        offset[0], offset[1], "Hand %s, %s, First 8 Cards" % (self.board.id, position.name))
    for i in range(8):
      offset = _Offsets(
        position.firstEightOffset,
        (0, _FIRST_LABEL_HEIGHT + _FIRST_LABEL_MARGIN),
        ((i%4)*_IMG_WIDTH+_IMG_MARGIN, math.floor(i/4)*(_IMG_HEIGHT+_IMG_MARGIN)))
      path = os.path.join(os.path.split(__file__)[0], "3/kl%s.jpg" % cards[i].id)
      self.canvas.drawImage(path, offset[0], offset[1], _IMG_WIDTH, -_IMG_HEIGHT)

  def _RenderFull(self, position):
    cards = self.board.GetFull(position)

    for color in _COLORS + [_SPECIAL_COLOR]:
      self.canvas.setFillColorRGB(
          float(color.rgbcolor[0])/256,
          float(color.rgbcolor[1])/256,
          float(color.rgbcolor[2])/256)

      if color.GetSymbol():
        offset = _Offsets(position.fullOffset, color.offset, (0, 1))
        color.GetSymbol().drawOn(self.canvas, offset[0], offset[1])

      cardNames = []
      for i in range(14):
        if cards[i].color == color:
          cardNames.append(str(cards[i].shortName))
      self.canvas.setFont('Helvetica', 10)
      offset = _Offsets(position.fullOffset, color.offset, (_COLOR_ID_WIDTH, 0))
      self.canvas.drawString(offset[0], offset[1],  ' '.join(cardNames))

  def _RenderCenter(self):
    self.canvas.setStrokeColorRGB(0, 0, 0)
    self.canvas.setFillColorRGB(1, 1, 1)
    self.canvas.setLineWidth(.5)
    offset = _Offsets((_CENTER_X, _CENTER_Y))
    self.canvas.rect(offset[0], offset[1], _CENTER_WIDTH, -_CENTER_HEIGHT)

    self.canvas.setFillColorRGB(0, 0, 0)

    # TODO: Calculate line height instead of eyeballing half of it for offset.
    offset = _Offsets((_CENTER_X, _CENTER_Y), (_CENTER_WIDTH / 2, _CENTER_HEIGHT / 2), (0, 14))
    self.canvas.setFont('Helvetica-Bold', 40)
    self.canvas.drawCentredString(offset[0], offset[1], str(self.board.id))

    self.canvas.setFont('Helvetica-Bold', 10)
    i = 180
    for position in _POSITIONS:
      self.canvas.saveState()
      offset = _Offsets(position.labelOffset)
      self.canvas.translate(offset[0], offset[1])
      self.canvas.rotate(i)
      i -= 90
      self.canvas.drawCentredString(0, 0, position.name)
      self.canvas.restoreState()


def GenerateBoards(count):
  '''Returns a list of randomly generated boards.

  Args:
    count: Integer. Number of boards to generate.
  '''
  for id in range(1,count+1):
    yield Board(id)


def RenderToIo(boards, write_target):
  """Renders the given boards to the passed output stream."""
  c = canvas.Canvas(write_target, pagesize=LETTER)
  for board in boards:
    _BoardRenderer(board, c).Render()
  c.save()
