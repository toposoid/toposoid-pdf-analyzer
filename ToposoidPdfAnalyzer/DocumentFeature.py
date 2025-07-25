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

import abc
from typing import List, Tuple
import numpy as np
from .DocumentFeatureCondition import DocumentFeatureCondition
from .model import PdfPageInfo

class DocumentFeature(metaclass=abc.ABCMeta):    
    """A class that represents the characteristics of a document
    """
    regexFrequencyDict = {}
    captionFrequencyDict = {} 
    adoptedDocumentFeatureCondition = None
    adoptedFrequencyForIndex = 0
    x0ForIndices = []

    @abc.abstractmethod
    def isIndexMatch(self, text:str, coordinate:int) -> bool:
        raise NotImplementedError()
    
    @abc.abstractmethod
    def isCaptionMatch(self, text: str) -> bool:
        raise NotImplementedError()
    
    @abc.abstractmethod
    def getPriority(self) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def getX0ForIndices(self) -> List[int]:
        raise NotImplementedError()

    @abc.abstractmethod
    def isLongProposition(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def isRepresentativeIndex(self, text:str) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def isPageDivisionTarget(self, ) -> bool:
        raise NotImplementedError()

    def getX0ForIndices(self) -> List[int]:
        """The PDF X0 coordinate of the paragraph start heading candidate is converted to an integer. This frequency is used to determine the paragraph start heading.

        Returns:
            List[int]: 
        """
        return self.x0ForIndices

    def isLongProposition(self) -> bool:
        """True if paragraphs containing many sentences are allowed, otherwise False, e.g. in contracts.

        Returns:
            bool: 
        """
        return self.documentFeatureCondition.longProposition

    def getPriority(self) -> int:
        """Priority among multiple document features.

        Returns:
            int: 
        """
        return self.documentFeatureCondition.priority

    def isPageDivisionTarget(self) -> bool:
        """rue to force paragraphs on pages, False otherwise.

        Returns:
            bool: 
        """
        return self.documentFeatureCondition.pageDivisionTarget
    
    def checkPageDivisionTarget(self, pageInfo:PdfPageInfo) -> bool:
        """If pageDivisionTarget is True, override this in the child class.

        Args:
            pageInfo (PdfPageInfo): 

        Returns:
            bool: 
        """
        return False

    def isRepresentativeIndex(self, text:str) -> bool:
        """True if it matches the regular expression that represents the first line of the finalized paragraph, otherwise False

        Args:
            text (str): 

        Returns:
            bool: 
        """
        if self.adoptedDocumentFeatureCondition is None:
            return False
        else:
            resultDict = self.adoptedDocumentFeatureCondition.isMatch(text)
            return list(resultDict.values())[0]

    def isIndexMatch(self, text:str, coordinate:int) -> bool:
        """Check if text matches document index format

        Args:
            text (str): 
            coordinate (int): 

        Returns:
            bool: 
        """
        hit = False
        resultDict = {}
        for regexConditionList in dict(sorted(self.documentFeatureCondition.regexIndexDict.items())).values(): #優先度の高い順にソート
            #Matches all regular expressions with the same priority
            for regexCondition in regexConditionList:
                resultDict |= regexCondition.isMatch(text)
            matchRegexList = list(map(lambda x:  x[0], list(filter(lambda y: y[1], resultDict.items()))))
            if len(matchRegexList) > 0:
                for regex in matchRegexList:
                    if regex in self.regexFrequencyDict:
                        self.regexFrequencyDict[regex].append(coordinate)
                    else:
                        self.regexFrequencyDict[regex] = [coordinate]                
                hit = True
                return hit
        return hit

    def isCaptionMatch(self, text: str) -> bool: 
        """Check if caption matches regular expression

        Args:
            text (str): 

        Returns:
            bool: 
        """
        
        hit = False
        resultDict = {}
        for captionConditionList in dict(sorted(self.documentFeatureCondition.regexCaptionDict.items())).values(): #優先度の高い順にソート
            #Matches all regular expressions with the same priority
            for captionCondition in captionConditionList:
                resultDict |= captionCondition.isMatch(text)
            matchCaptionList = list(map(lambda x:  x[0], list(filter(lambda y: y[1], resultDict.items()))))
            if len(matchCaptionList) > 0:
                for regex in matchCaptionList:
                    if regex in self.captionFrequencyDict:
                        self.captionFrequencyDict[regex] += 1
                    else:
                        self.captionFrequencyDict[regex] = 1
                hit = True
                return hit        
        
        return hit

    def getCoordinates(self, coordinates):    
        """For each candidate first line of a paragraph, the most frequent representative coordinates are extracted.

        Args:
            coordinates (_type_): 

        Returns:
            _type_: 
        """
        #If the difference between the maximum and minimum frequency of occurrence is large, the coordinates with the highest frequency of occurrence (80% tile) are used. 
        #ex.[25,35,1,1,1,1,1,1,1,1] → [25, 35]
        #In cases like [2,2,1], all are accepted
        u, count = np.unique(list(map(lambda x: int(x), coordinates)), return_counts=True)
        
        if max(count)-min(count) < 5:
            return list(u), sum(count)
        else:
            #Since all the coordinates may be the same, we include an equal sign.
            pairs = list(filter(lambda x: x[1] >= np.percentile(sorted(count), 80) , zip(u, count)))
            return list(map(lambda x: x[0], pairs)), sum(list(map(lambda x: x[1], pairs)))

    
    def getRegexAndCoordinateAndFrequencyForIndex(self) -> Tuple[str, List[int], int]:
        """Get the regular expression and coordinate position that best describes this document feature.

        Returns:
            Tuple[str, List[int], int]:
        """
        #The higher the priority, the higher the frequency.
        #If there are multiple items with the same priority, the higher the frequency, the higher the frequency.
        adoptedCondition = None        
        adoptedCoordinates= []
        adoptedFrequency = 0
        
        for regexConditionList in dict(sorted(self.documentFeatureCondition.regexIndexDict.items())).values():
            hitMax = 0            
            for condition in regexConditionList: #同一プライオリティのループ
                if condition.regex in self.regexFrequencyDict and len(self.regexFrequencyDict[condition.regex]) > hitMax:
                    hitMax = len(self.regexFrequencyDict[condition.regex])                    
                    adoptedCondition = condition
                    adoptedCoordinates, adoptedFrequency = self.getCoordinates(self.regexFrequencyDict[condition.regex])
            if adoptedCondition is not None:                
                self.adoptedDocumentFeatureCondition = adoptedCondition
                self.adoptedFrequencyForIndex = adoptedFrequency
                self.x0ForIndices = adoptedCoordinates
                return self.adoptedDocumentFeatureCondition, self.x0ForIndices, self.adoptedFrequencyForIndex

        return self.adoptedDocumentFeatureCondition, self.x0ForIndices, self.adoptedFrequencyForIndex
    

    def getFrequencyForCaption(self):
        """Get the frequency of document feature caption expressions

        Returns:
            _type_: 
        """
        adoptedFrequency = 0
        for frequency in self.captionFrequencyDict.values():
            adoptedFrequency += frequency
        return adoptedFrequency
    
    def getFrequencyForIndex(self):
        """Get the frequency of document feature index expressions

        Returns:
            _type_: 
        """
        return self.adoptedFrequencyForIndex
    
    def clear(self):
        self.regexFrequencyDict = {}
        self.captionFrequencyDict = {} 
        self.adoptedDocumentFeatureCondition = None
        self.adoptedFrequencyForIndex = 0
        self.x0ForIndices = []
  