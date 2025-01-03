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


from copy import copy
from operator import mul
from random import shuffle

from card import Card
from symbols import Direction, Rank, Suit


# See http://mail.python.org/pipermail/edu-sig/2001-May/001288.html for details.
comb = lambda n, k: reduce(mul, range(n, n-k, -1)) / reduce(mul, range(1, k+1))


# TODO: consider making Hand a subclass of List, with additional constraints.

class Deck(object):
    """A Deck object provides operations for dealing Card objects.
    
    A hand is a collection of 13 cards from the deck.
    A deal is a distribution of all 52 cards to four hands.
    
    A deal is represented as a dictionary, mapping Direction labels to
    lists (hands) of Card objects.
    
    There are exactly 52! / (13!)**4 (comb(52,13) * comb(39,13) * comb(26,13))
    distinct deals of 13 cards to 4 positions from a standard 52-card deck.
    """

    cards = [Card(r, s) for r in Rank for s in Suit]
    cardSeq = copy(cards)
    cardSeq.sort(reverse=True)  # Required order: Ace of Spades -> Two of Clubs.

    Nmax = comb(52, 13)
    Emax = comb(39, 13)
    Smax = comb(26, 13)
    D = Nmax * Emax * Smax


    def isValidDeal(self, deal):
        """Checks that structure of deal conforms to requirements:

          * 4-element dict, mapping Direction objects to hand lists.
          * Hand lists contain exactly 13 Card objects.
          * No card may be repeated in the same hand, or between hands.
          * The cards in hands may be in any order.

        @param deal: a deal dict.
        @return: True if deal is valid, False otherwise.
        """
        return True  # TODO - if invalid, perhaps give reason


    def randomDeal(self):
        """Shuffles the deck and generates a random deal of hands.
        
        @return: a deal dictionary.
        """
        shuffle(self.cards)
        hands = {}
        for position in Direction:
            hands[position] = []
        for index, card in enumerate(self.cards):
            hands[Direction[index % len(Direction)]].append(card)
        for hand in hands.values():
            hand.sort()
        return hands


    def dealToIndex(self, deal):
        """Computes the index which corresponds to the specified deal.
        
        This implements the "impossible bridge book" encoding algorithm by
        Thomas Andrews, see http://bridge.thomasoandrews.com/impossible/.
        
        @param deal: dict representing a valid deal.
        @return: integer in range 0..D-1
        """
        assert self.isValidDeal(deal)

        cardSeq = copy(self.cardSeq)  # Make a copy for modification.
        indexes = {}

        # For each hand, compute indexes of cards in cardSeq.
        for position in (Direction.North, Direction.East, Direction.South):
            indexes[position] = 0
            deal[position].sort(reverse=False)
            # It is desirable to remove cards from cardSeq when adding their
            # indexes, instead of doing so in an extra step.
            # Removing cards backwards preserves the indexes of later cards.
            for i, card in enumerate(deal[position]):
                indexes[position] += comb(cardSeq.index(card), 13-i)
                cardSeq.remove(card)

        # Deal index = (Nindex * Emax * Smax) + (Eindex * Smax) + Sindex
        indexes[Direction.North] *= self.Emax * self.Smax
        indexes[Direction.East]  *= self.Smax
        return long(sum(indexes.values()))


    def indexToDeal(self, num):
        """Generates the deal which corresponds to the specified index.
        
        This implements the "impossible bridge book" decoding algorithm by
        Thomas Andrews, see http://bridge.thomasoandrews.com/impossible/.
        
        @param num: integer in range 0..D-1.
        @return: dict representing a valid deal.
        """
        assert type(num) in (int, long), "index must be an integer"
        assert 0 <= num < self.D, "index not in required range"

        cardSeq = copy(self.cardSeq)  # Make a copy for modification.
        deal = {}

        # Split index into hand indexes.
        indexes = {Direction.North : (num / self.Smax) / self.Emax,
                   Direction.East  : (num / self.Smax) % self.Emax,
                   Direction.South : (num % self.Smax) }

        for position in (Direction.North, Direction.East, Direction.South):
            deal[position] = []
            for k in range(13, 0, -1):
                # Find the largest n such that comb(n, k) <= indexes[position].
                n = k-1  # n < k implies comb(n, k) = 0

                # comb(n+1, k) =
                #   n-k = -1  => comb(n, k) * (n+1)
                #   otherwise => (comb(n, k) * (n+1)) / (n+1 - k)
                while comb(n+1, k) <= indexes[position]:
                    n += 1

                # Remove card index from indices, add card to hand.
                indexes[position] -= comb(n, k)
                card = cardSeq[n]
                deal[position].append(card)
                cardSeq.remove(card)

        deal[Direction.West] = cardSeq  # West has the remaining cards.
        return deal



    __pbnDirection = dict(zip('NESW', Direction) + zip(Direction, 'NESW'))
    __pbnRank = dict(zip('23456789TJQKA', Rank) + zip(Rank, '23456789TJQKA'))


    def fromString(self, dealstr):
        """Generates the deal which corresponds to the given PBN deal string.
        
        As per the PBN specification, the given deal string should conform to
        the format "<first>:<1st_hand> <2nd_hand> <3rd_hand> <4th_hand>".
        
        @param dealstr: a PBN deal string.
        @return: a Deal object containing the corresponding deal.
        """
        # Reconstruct deal.
        first, hands = dealstr.split(":")
        firstindex = self.__pbnDirection[first.strip()].index
        order = Direction[firstindex:] + Direction[:firstindex]

        deal = dict((pos, []) for pos in Direction)

        for position, hand in zip(order, hands.strip().split(' ')):
            for suit, suitcards in zip(reversed(Suit), hand.split('.')):
                for rank in suitcards:
                    card = Card(self.__pbnRank[rank], suit)
                    deal[position].append(card)

        return deal
