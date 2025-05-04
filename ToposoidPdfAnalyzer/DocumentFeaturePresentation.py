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
from .model import PdfPageInfo

class DocumentFeaturePresentation(DocumentFeature):
    """For presentation documents

    Args:
        DocumentFeature (_type_): 
    """
    
    def __init__(self):

        self.documentFeatureCondition:DocumentFeatureCondition = DocumentFeatureCondition()
        self.documentFeatureCondition.regexIndexDict = {}
        self.documentFeatureCondition.regexCaptionDict = {}
        self.documentFeatureCondition.priority = 10
        self.documentFeatureCondition.longProposition = True
        self.documentFeatureCondition.pageDivisionTarget = True
        self.documentFeatureCondition.isOnlyHeaderLine = False

    def checkPageDivisionTarget(self, pageInfo:PdfPageInfo):
        """Evaluate whether it is a presentation material or not.
        Args:
            pageInfo (PdfPageInfo): 

        Returns:
            _type_: 
        """
        result = False
        #ref. https://support.microsoft.com/en-us/office/change-the-size-of-your-slides-040a811c-be43-40b9-8d04-0de5ed79987e
        #When you create a new slide, it will be displayed with an aspect ratio of 16:9. In the past, PowerPoint slides had a default aspect ratio of 4:3, but since PowerPoint 2013, 16:9 has become the default.
        ratio =  pageInfo.width/pageInfo.height
        if abs(ratio-4/3) < 0.01 or  abs(ratio-16/9) < 0.01:
            #All slides should use a minimum font size of 24 points.
            #ref. https://www.arl.org/accessibility-guidelines-for-powerpoint-presentations/        
            #ref. https://studio.virtual-planner.com/powerpoint-font-size/
            if pageInfo.mainFontSize > 16:
                result = True
        return result
