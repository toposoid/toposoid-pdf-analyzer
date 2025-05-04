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
import numpy as np
from .DocumentFeatureCondition import DocumentFeatureCondition

class DocumentFeatureOther(DocumentFeature):
    """For others

    Args:
        DocumentFeature (_type_): _description_
    """
    
    def __init__(self):

        self.documentFeatureCondition:DocumentFeatureCondition = DocumentFeatureCondition()
        self.documentFeatureCondition.regexIndexDict = {}
        self.documentFeatureCondition.regexCaptionDict = {}
        self.documentFeatureCondition.priority = np.inf
        self.documentFeatureCondition.longProposition = False
        self.documentFeatureCondition.pageDivisionTarget = False
        self.documentFeatureCondition.isOnlyHeaderLine = False
    
