# PyBridge -- online contract bridge made easy.
# Copyright (C) 2004-2007 PyBridge Project.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


import gtk
from wrapper import GladeWrapper

from pybridge.network.client import client
from pybridge.network.error import GameError

from cardarea import CardArea
from config import config
from eventhandler import SimpleEventHandler
from manager import WindowManager
from vocabulary import *

from window_bidbox import WindowBidbox


class WindowBridgetable(GladeWrapper):

    glade_name = 'window_bridgetable'


    def setUp(self):
        self.children = WindowManager()
        self.eventHandler = SimpleEventHandler(self)

        self.table = None  # Table currently displayed in window.
        self.player, self.position = None, None

        # Set up "Take Seat" menu.
        self.takeseat_items = {}
        menu = gtk.Menu()
        for position in Direction:
            item = gtk.MenuItem(DIRECTION_NAMES[position], True)
            item.connect('activate', self.on_seat_activated, position)
            item.show()
            menu.append(item)
            self.takeseat_items[position] = item
        self.takeseat.set_menu(menu)

        # Set up CardArea widget.
        self.cardarea = CardArea()
        self.cardarea.on_card_clicked = self.on_card_clicked
        self.cardarea.on_hand_clicked = self.on_hand_clicked
        self.cardarea.set_size_request(640, 480)
        self.scrolled_cardarea.add_with_viewport(self.cardarea)
        self.cardarea.show()

        renderer = gtk.CellRendererText()
        renderer.set_property('size-points', 12)
        renderer.set_property('xalign', 0.5)

        # Set up bidding history and column display.
        self.call_store = gtk.ListStore(str, str, str, str)
        self.biddingview.set_model(self.call_store)
        for index, position in enumerate(Direction):
            title = DIRECTION_NAMES[position]
            column = gtk.TreeViewColumn(title, renderer, markup=index)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)
            self.biddingview.append_column(column)

        # Set up trick history and column display.
        self.trick_store = gtk.ListStore(str, str, str, str)
        self.trickview.set_model(self.trick_store)
        for index, position in enumerate(Direction):
            title = DIRECTION_NAMES[position]
            column = gtk.TreeViewColumn(str(title), renderer, markup=index)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)
            self.trickview.append_column(column)

        renderer = gtk.CellRendererText()

        # Set up score sheet and column display.
        self.score_store = gtk.ListStore(str, str, str, str)
        self.scoresheet.set_model(self.score_store)
        for index, title in enumerate([_('Contract'), _('Made'), _('N/S'), _('E/W')]):
            column = gtk.TreeViewColumn(title, renderer, markup=index)
            self.scoresheet.append_column(column)

        # Set up observer listing.
        self.observer_store = gtk.ListStore(str)
        self.treeview_observers.set_model(self.observer_store)
        column = gtk.TreeViewColumn(None, renderer, text=0)
        self.observer_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.treeview_observers.append_column(column)


    def tearDown(self):
        # Close all child windows.
        for window in self.children.values():
            self.children.close(window)

        self.table = None  # Dereference table.


    def errback(self, failure):
        print "Error: %s" % failure.getErrorMessage()
        #print failure.getBriefTraceback()


    def setTable(self, table):
        """Changes display to match the table specified.
        
        @param table: the (now) focal table.
        """
        self.table = table
        self.table.attach(self.eventHandler)
        self.table.game.attach(self.eventHandler)
        self.player, self.position = None, None

        self.window.set_title(_('Table %s (Bridge)') % self.table.id)
        self.resetGame()

        for position in Direction:
            self.redrawHand(position)  # Redraw all hands.

        if self.table.game.inProgress():
            # If trick play in progress, redraw trick.
            if self.table.game.play:
                self.redrawTrick()
            self.setTurnIndicator()

            for call in self.table.game.bidding.calls:
                position = self.table.game.bidding.whoCalled(call)
                self.addCall(call, position)

            self.setDealer()
            self.setVulnerability()

            # If contract, set contract.
            if self.table.game.bidding.isComplete():
                self.setContract()

            # If playing, set trick counts.
            if self.table.game.play:
                for position, cards in self.table.game.play.played.items():
                    for card in cards:
                        self.addCard(card, position)
                self.setTrickCount()

            # If user is a player and bidding in progress, open bidding box.
            if self.player and not self.table.game.bidding.isComplete():
                bidbox = self.children.open(WindowBidbox, parent=self)
                bidbox.setCallSelectHandler(self.on_call_selected)
                bidbox.setTable(self.table, self.position)


        # Initialise seat menu and player labels.
        for position in Direction:
            player = self.table.players.get(position)  # Player name or None.

            available = player is None or position == self.position
            self.takeseat_items[position].set_property('sensitive', available)
            if player:
                self.event_joinGame(player, position)
            else:  # Position vacant.
                self.event_leaveGame(None, position)

        # Initialise observer listing.
        self.observer_store.clear()
        for observer in self.table.observers:
            self.event_addObserver(observer)


    def resetGame(self):
        """Clears bidding history, contract, trick counts."""
#        self.cardarea.clear()
        self.call_store.clear()   # Reset bidding history.
        self.trick_store.clear()  # Reset trick history.
        self.setContract()    # Reset contract.
        self.setTrickCount()  # Reset trick counts.


    def addCall(self, call, position):
        """Adds call from specified player, to bidding tab."""
        column = position.index
        if column == 0 or self.call_store.get_iter_first() == None:
            iter = self.call_store.append()
        else:  # Get bottom row. There must be a better way than this...
            iter = self.call_store.get_iter_first()
            while self.call_store.iter_next(iter) != None:
                iter = self.call_store.iter_next(iter)

        format = render_call(call)
        self.call_store.set(iter, column, format)


    def addCard(self, card, position):
        """"""
        position = self.table.game.play.whoPlayed(card)
        column = position.index
        row = self.table.game.play.played[position].index(card)

        if self.trick_store.get_iter_first() == None:
            self.trick_store.append()
        iter = self.trick_store.get_iter_first()
        for i in range(row):
            iter = self.trick_store.iter_next(iter)
            if iter is None:
                iter = self.trick_store.append()

        format = render_card(card)
        self.trick_store.set(iter, column, format)


    def addScore(self, contract, made, score):
        textContract = render_contract(contract)
        textMade = '%s' % made
        if contract['declarer'] in (Direction.North, Direction.South) and score > 0 \
        or contract['declarer'] in (Direction.East, Direction.West) and score < 0:
            textNS, textEW = '%s' % abs(score), ''
        else:
            textNS, textEW = '', '%s' % abs(score)
        self.score_store.prepend([textContract, textMade, textNS, textEW])


    def gameComplete(self):
        # Display all previously revealed hands - the server will reveal the others.
        for position in self.table.game.visibleHands:
            self.redrawHand(position, all=True)

        self.setTurnIndicator()

        dialog = gtk.MessageDialog(parent=self.window, type=gtk.MESSAGE_INFO)
        dialog.set_title(_('Game result'))

        # Determine and display score in dialog box.
        if self.table.game.contract:
            declarerWon, defenceWon = self.table.game.play.getTrickCount()
            required = self.table.game.contract['bid'].level.index + 7
            offset = declarerWon - required
            score = self.table.game.getScore()
            self.addScore(self.table.game.contract, declarerWon, score)

            fields = {'contract': render_contract(self.table.game.contract),
                      'offset': abs(offset) }
            if offset > 0:
                if offset == 1:
                    resultText = _('Contract %(contract)s made by 1 trick.') % fields
                else:
                    resultText = _('Contract %(contract)s made by %(offset)s tricks.') % fields
            elif offset < 0:
                if offset == -1:
                    resultText = _('Contract %(contract)s failed by 1 trick.') % fields
                else:
                    resultText = _('Contract %(contract)s failed by %(offset)s tricks.') % fields
            else:
                resultText = _('Contract %(contract)s made exactly.') % fields
            pair = (score >= 0 and _('declarer')) or _('defence')
            scoreText = _('Score %(points)s points for %(pair)s.') % {'points': abs(score), 'pair': pair}
            if self.table.game.board.has_key('pbn_result'):
                pbnText=self.table.game.board['pbn_result']
                dialog.set_markup(resultText+'\n'+pbnText+'\n'+scoreText)
            else:
                dialog.set_markup(resultText + '\n' + scoreText)
        else:
            dialog.set_markup(_('Bidding passed out.'))
            dialog.format_secondary_text(_('No score.'))

        if self.player:
            dialog.add_button(_('Leave Seat'), gtk.RESPONSE_CANCEL)
            dialog.format_secondary_text(_('Click OK to start next game.'))
        dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        dialog.set_default_response(gtk.RESPONSE_OK)
        # If user leaves table (ie. closes window), close dialog as well.
        dialog.set_transient_for(self.window)
        dialog.set_destroy_with_parent(True)

        def dialog_response_cb(dialog, response_id):
            dialog.destroy()
            if self.player:
                if response_id == gtk.RESPONSE_OK and self.table.game.isNextGameReady():
                    d = self.player.callRemote('startNextGame')
                    d.addErrback(self.errback)
                elif response_id == gtk.RESPONSE_CANCEL:
                    self.on_leaveseat_clicked(dialog)

        dialog.connect('response', dialog_response_cb)
        dialog.show()


    def redrawHand(self, position, all=False):
        """Redraws cards making up the hand at position.
        
        Cards played are filtered out and omitted from display.
        Unknown cards are displayed face down.
        
        @param position:
        @param all: If True, do not filter out cards played.
        """
        try:
            hand = self.table.game.getHand(position)
            facedown = False
        except GameError:  # Unknown hand.
            hand = range(13)
            facedown = True

        if all is True or self.table.game.play is None:
            available = hand
        else:
            played = self.table.game.play.played[position]
            if facedown:  # Draw cards face down for unknown hand. 
                available = range(13 - len(played))
            else:
                available = [card for card in hand if card not in played]

        self.cardarea.set_hand(hand, position, facedown, visible=available)


    def redrawTrick(self):
        """Redraws trick.
        
        @param table:
        @param trick:
        """
        trick = None
        if self.table.game.play:
            trick = self.table.game.play.getCurrentTrick()
        self.cardarea.set_trick(trick)


# Methods to set information displayed on side panel.


    def setContract(self):
        """Sets the contract label from contract."""
        format = "<span size=\"x-large\">%s</span>"

        if self.table.game.contract:
            text = render_contract(self.table.game.contract)
            self.label_contract.set_markup(format % text)
            self.label_contract.set_property('sensitive', True)
        else:
            self.label_contract.set_markup(format % _('No contract'))
            self.label_contract.set_property('sensitive', False)


    def setDealer(self):
        format = "<b>%s</b>"

        dealer = ''
        if self.table.game.inProgress():
            dealer = DIRECTION_NAMES[self.table.game.board['dealer']]

        self.label_dealer.set_markup(format % dealer)


    def setTrickCount(self):
        """Sets the trick counter labels for declarer and defence."""
        format = "<span size=\"x-large\"><b>%s</b> (%s)</span>"

        if self.table.game.play:
            declarer, defence = self.table.game.play.getTrickCount()
            required = self.table.game.contract['bid'].level.index + 7
            declarerNeeds = max(0, required - declarer)
            defenceNeeds = max(0, 13 + 1 - required - defence)

            self.label_declarer.set_markup(format % (declarer, declarerNeeds))
            self.label_defence.set_markup(format % (defence, defenceNeeds))
            self.frame_declarer.set_property('sensitive', True)
            self.frame_defence.set_property('sensitive', True)

        else:  # Reset trick counters.
            self.label_declarer.set_markup(format % (0, 0))
            self.label_defence.set_markup(format % (0, 0))
            self.frame_declarer.set_property('sensitive', False)
            self.frame_defence.set_property('sensitive', False)


    def setTurnIndicator(self):
        """Sets the statusbar text to indicate which player is on turn."""
        context = self.statusbar.get_context_id('turn')
        self.statusbar.pop(context)

        try:
            turn = self.table.game.getTurn()

            if self.table.game.play:
                declarer, dummy = self.table.game.play.declarer, self.table.game.play.dummy
                if self.position and self.position == turn != dummy:
                    text = _("Play a card from your hand.")
                elif self.position and self.position == declarer and turn == dummy:
                    text = _("Play a card from dummy's hand.")
                else:
                    text = _("It is %s's turn to play a card.") % DIRECTION_NAMES[turn]

            else:  # Bidding.
                if self.position and self.position == turn:
                    text = _("Make a call from the bidding box.")
                else:
                    text = _("It is %s's turn to make a call.") % DIRECTION_NAMES[turn]

        except GameError:  # Game not in progress.
            text = _("Waiting for next game to start.")

        self.statusbar.push(context, text)

    def setVulnerability(self):
        """Sets the vulnerability indicators."""
        format = "<b>%s</b>"

        vulnerable = ''
        if self.table.game.inProgress():
            vulnerable = VULN_SYMBOLS[self.table.game.board['vuln']]

        self.label_vuln.set_markup(format % vulnerable)


# Registered event handlers.


    def event_addObserver(self, observer):
        self.observer_store.append([observer])


    def event_removeObserver(self, observer):

        def func(model, path, iter, user_data):
            if model.get_value(iter, 0) in user_data:
                model.remove(iter)
                return True

        self.observer_store.foreach(func, observer)


    def event_joinGame(self, player, position):
        self.cardarea.set_player_name(position, player)
        # Disable menu item corresponding to position.
        widget = self.takeseat_items[position]
        widget.set_property('sensitive', False)

        # If all positions occupied, disable Take Seat.
        if len(self.table.players.values()) == len(Direction):
            self.takeseat.set_property('sensitive', False)

        if self.player and self.table.game.isNextGameReady():
            d = self.player.callRemote('startNextGame')
            d.addErrback(self.errback)


    def event_leaveGame(self, player, position):
        self.cardarea.set_player_name(position, None)
        # Enable menu item corresponding to position.
        widget = self.takeseat_items[position]
        widget.set_property('sensitive', True)

        # If we are not seated, ensure Take Seat is enabled.
        if self.position is None:
            self.takeseat.set_property('sensitive', True)


    def event_start(self, board):
        #self.children.close('dialog_gameresult')
        self.resetGame()

        self.redrawTrick()  # Clear trick.
        for position in Direction:
            self.redrawHand(position)

        self.setTurnIndicator()
        self.setDealer()
        self.setVulnerability()

        if self.player:
            d = self.player.callRemote('getHand')
            # When player's hand is returned by server, reveal it to client-side Game.
            # TODO: is there a better way of synchronising hands?
            d.addCallbacks(self.table.game.revealHand, self.errback,
                           callbackKeywords={'position' : self.position})
            bidbox = self.children.open(WindowBidbox, parent=self)
            bidbox.setCallSelectHandler(self.on_call_selected)
            bidbox.setTable(self.table, self.position)


    def event_makeCall(self, call, position):
        self.addCall(call, position)
        self.setTurnIndicator()

        if self.table.game.bidding.isComplete():
            self.setContract()
            if self.children.get(WindowBidbox):  # If a player.
                self.children.close(self.children[WindowBidbox])

        if not self.table.game.inProgress():
            self.gameComplete()


    def event_playCard(self, card, position):
        # Determine the position of the hand from which card was played.
        playfrom = self.table.game.play.whoPlayed(card)
        self.addCard(card, playfrom)
        self.setTurnIndicator()
        self.setTrickCount()
        self.redrawTrick()
        self.redrawHand(playfrom)
        
        if not self.table.game.inProgress():
            self.gameComplete()


    def event_revealHand(self, hand, position):
        all = not self.table.game.inProgress()  # Show all cards if game has finished.
        self.redrawHand(position, all)


    def event_sendMessage(self, message, sender, recipients):
        buffer = self.chat_messagehistory.get_buffer()
        iter = buffer.get_end_iter()
        buffer.insert(iter, '\n' + _('%(sender)s: %(message)s' % {'sender': sender, 'message': message}))
        self.chat_messagehistory.scroll_to_iter(iter, 0)


# Signal handlers.


    def on_call_selected(self, call):
        if self.player:
            d = self.player.callRemote('makeCall', call)
            d.addErrback(self.errback)


    def on_hand_clicked(self, position):
        if not self.player and not self.table.players.get(position):
            # Join game at position.
            self.on_seat_activated(self.cardarea, position)


    def on_card_clicked(self, card, position):
        if self.player:
            if self.table.game.inProgress() and self.table.game.play:
                d = self.player.callRemote('playCard', card)
                d.addErrback(self.errback)


    def on_seat_activated(self, widget, position):
        
        def success(player):
            self.player = player  # RemoteReference to BridgePlayer object.
            self.position = position

            self.takeseat.set_property('sensitive', False)
            self.leaveseat.set_property('sensitive', True)

            self.cardarea.set_player_mapping(self.position)

            if self.table.game.inProgress():
                d = self.player.callRemote('getHand')
                d.addCallbacks(self.table.game.revealHand, self.errback,
                               callbackKeywords={'position' : self.position})

                # If game is running and bidding is active, open bidding box.
                if not self.table.game.bidding.isComplete():
                    bidbox = self.children.open(WindowBidbox, parent=self)
                    bidbox.setCallSelectHandler(self.on_call_selected)
                    bidbox.setTable(self.table, self.position)

        d = self.table.joinGame(position)
        d.addCallbacks(success, self.errback)


    def on_takeseat_clicked(self, widget, *args):
        # TODO: match user up with preferred partner.
        for position in Direction:
            if position not in self.table.players:  # Position is vacant.
                self.on_seat_activated(widget, position)  # Take position.
                break


    def on_leaveseat_clicked(self, widget, *args):

        def success(r):
            self.player = None
            self.position = None
            self.takeseat.set_property('sensitive', True)
            self.leaveseat.set_property('sensitive', False)
            if self.children.get(WindowBidbox):
                self.children.close(self.children[WindowBidbox])

        d = self.table.leaveGame(self.position)
        d.addCallbacks(success, self.errback)


    def on_toggle_gameinfo_clicked(self, widget, *args):
        visible = self.toggle_gameinfo.get_active()
        self.gameinfo.set_property('visible', visible)


    def on_toggle_chat_clicked(self, widget, *args):
        visible = self.toggle_chat.get_active()
        self.chatbox.set_property('visible', visible)


    def on_toggle_fullscreen_clicked(self, widget, *args):
        if self.toggle_fullscreen.get_active():
            self.window.fullscreen()
        else:
            self.window.unfullscreen()


    def on_leavetable_clicked(self, widget, *args):
        # If user is currently playing a game, request confirmation.
        if self.player and self.table.game.inProgress():
            dialog = gtk.MessageDialog(parent=self.window, flags=gtk.DIALOG_MODAL,
                                       type=gtk.MESSAGE_QUESTION)
            dialog.set_title(_('Leave table?'))
            dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dialog.add_button(_('Leave Table'), gtk.RESPONSE_OK)
            dialog.set_markup(_('Are you sure you wish to leave this table?'))
            dialog.format_secondary_text(_('You are currently playing a game. Leaving may forfeit the game, or incur penalties.'))

            def dialog_response_cb(dialog, response_id):
                dialog.destroy()
                if response_id == gtk.RESPONSE_OK:
                    d = client.leaveTable(self.table.id)
                    d.addErrback(self.errback)

            dialog.connect('response', dialog_response_cb)
            dialog.show()

        else:
            d = client.leaveTable(self.table.id)
            d.addErrback(self.errback)


    def on_chat_message_changed(self, widget, *args):
        sensitive = self.chat_message.get_text() != ''
        self.chat_send.set_property('sensitive', sensitive)


    def on_chat_send_clicked(self, widget, *args):
        message = self.chat_message.get_text()
        if message:  # Don't send a null message.
            self.chat_send.set_property('sensitive', False)
            self.chat_message.set_text('')  # Clear message.
            self.table.sendMessage(message)


    def on_window_delete_event(self, widget, *args):
        self.on_leavetable_clicked(widget, *args)
        return True  # Stops window deletion taking place.

