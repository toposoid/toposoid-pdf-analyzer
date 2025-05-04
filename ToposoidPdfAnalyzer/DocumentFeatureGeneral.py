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

from .DocumentFeature  import DocumentFeature
from .DocumentFeatureCondition import DocumentFeatureRegexCondition
from .DocumentFeature import DocumentFeature
from .DocumentFeatureCondition import DocumentFeatureCondition

class DocumentFeatureGeneral(DocumentFeature):
    """For general documents

    Args:
        DocumentFeature (_type_): _description_
    """
    
    def __init__(self):

        dfrcIndex0 = DocumentFeatureRegexCondition(regex = r"^[0-9]+[\.\-\s].*\s")
        dfrcIndex1 = DocumentFeatureRegexCondition(regex = r"^[Ⅰ-Ⅹ]+[\.\-\s].*\s")
        dfrcIndex2 = DocumentFeatureRegexCondition(regex = r"^[IXV]+[\.\-\s].*\s")
        dfrcCaption0 = DocumentFeatureRegexCondition(regex = r".*")
        
        self.documentFeatureCondition:DocumentFeatureCondition = DocumentFeatureCondition()
        self.documentFeatureCondition.regexIndexDict = {0:[dfrcIndex0, dfrcIndex1, dfrcIndex2]}
        self.documentFeatureCondition.regexCaptionDict = {0:[dfrcCaption0]}
        self.documentFeatureCondition.priority = 100
        self.documentFeatureCondition.longProposition = False
        self.documentFeatureCondition.pageDivisionTarget = False
        self.documentFeatureCondition.isOnlyHeaderLine = True


