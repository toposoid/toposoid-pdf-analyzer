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
from .DocumentFeatureCondition import DocumentFeatureCondition
class DocumentFeatureJapaneseLegal(DocumentFeature):
    """For Japanese legal documents

    Args:
        DocumentFeature (_type_): 
    """
    
    def __init__(self):
        
        dfrcIndex0 = DocumentFeatureRegexCondition(
            regex = r"^[\(|【](.+?)[\)|】].*$",
            haveGroup = True,
            acceptRegexIndexGroupDict = {},
            rejectRegexIndexGroupDict = {1:[r"[0-9]+", r"[a-zA-Z]+"]},
            indexGroupMinLengthDict = {1:2}
        )

        dfrcIndex1 = DocumentFeatureRegexCondition(regex = r"^第[0-9]*.*条")
        dfrcCaption1 = DocumentFeatureRegexCondition(regex = r".*契約書")
        dfrcCaption2 = DocumentFeatureRegexCondition(regex = r".*同意書")

        self.documentFeatureCondition:DocumentFeatureCondition = DocumentFeatureCondition()
        self.documentFeatureCondition.regexIndexDict = {0:[dfrcIndex0], 1:[dfrcIndex1]}
        self.documentFeatureCondition.regexCaptionDict = {0:[dfrcCaption1, dfrcCaption2]}
        self.documentFeatureCondition.priority = 10
        self.documentFeatureCondition.longProposition = True
        self.documentFeatureCondition.pageDivisionTarget = False
        self.documentFeatureCondition.isOnlyHeaderLine = False

