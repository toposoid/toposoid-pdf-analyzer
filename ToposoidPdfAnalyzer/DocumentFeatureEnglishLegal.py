'''
  Copyright (C) 2025  Linked Ideal LLC.[https://linked-ideal.com/]
 
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as
  published by the Free Software Foundation, version 3.
 
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.
 
  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from .DocumentFeature import DocumentFeature
from .DocumentFeatureCondition import DocumentFeatureRegexCondition
from .DocumentFeature import DocumentFeature
from .DocumentFeatureCondition import DocumentFeatureCondition

class DocumentFeatureEnglishLegal(DocumentFeature):
    """For English legal documents

    Args:
        DocumentFeature (_type_): _description_
    """

    def __init__(self):
        dfrcIndex0 = DocumentFeatureRegexCondition(regex = r"^(Article|ARTICLE).*[0-9]*.*")
        dfrcIndex1 = DocumentFeatureRegexCondition(regex = r"^[0-9].*\.\s")
        dfrcIndex2 = DocumentFeatureRegexCondition(regex = r"^[Ⅰ-Ⅹ].*\.\s")
        dfrcIndex3 = DocumentFeatureRegexCondition(regex = r"^[IXV]+\.\s")
        dfrcCaption0 = DocumentFeatureRegexCondition(regex = r".*(Contract|CONTRACT)")
        dfrcCaption1 = DocumentFeatureRegexCondition(regex = r".*(Agreement|AGREEMENT)")
        
        self.documentFeatureCondition:DocumentFeatureCondition = DocumentFeatureCondition()
        self.documentFeatureCondition.regexIndexDict = {0:[dfrcIndex0, dfrcIndex1, dfrcIndex2, dfrcIndex3]}
        self.documentFeatureCondition.regexCaptionDict = {0:[dfrcCaption0, dfrcCaption1]}
        self.documentFeatureCondition.priority = 20
        self.documentFeatureCondition.longProposition = True
        self.documentFeatureCondition.pageDivisionTarget = False
        self.documentFeatureCondition.isOnlyHeaderLine = False