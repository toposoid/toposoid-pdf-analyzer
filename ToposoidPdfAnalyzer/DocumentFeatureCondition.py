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

from typing import List, Dict
import re

class DocumentFeatureRegexCondition():
    """Evaluate the regular expression set in DocumentFeatureCondition

    """
    regex:str = ""
    haveGroup:bool = False
    acceptRegexIndexGroupDict:Dict[int, str] = {}
    rejectRegexIndexGroupDict:Dict[int, str] = {}
    indexGroupMinLengthDict:Dict[int, int] = {}  
 
    def __init__(self, regex, haveGroup=False, acceptRegexIndexGroupDict={}, rejectRegexIndexGroupDict={}, indexGroupMinLengthDict={}):
        """constructor

        Args:
            regex (_type_): Regular expression to extract the first line of a paragraph
            haveGroup (bool, optional): True if the regular expression has groups. Defaults to False.
            acceptRegexIndexGroupDict (dict, optional): A key is priority, The value is a list of regular expressions. If a group expression of a regular expression matches, it is adopted as a feature of the document. Defaults to {}.
            rejectRegexIndexGroupDict (dict, optional): A key is priority, The value is a list of regular expressions. If no regular expression grouping matches, the document is considered a feature. Defaults to {}.
            indexGroupMinLengthDict (dict, optional): A key is priority, The value is a list of int. The minimum length of the string that the regular expression group expression matches. If the string is not longer than this length, it will not be evaluated.. Defaults to {}.
        """
        self.regex = regex
        self.haveGroup = haveGroup
        self.acceptRegexIndexGroupDict = acceptRegexIndexGroupDict
        self.rejectRegexIndexGroupDict = rejectRegexIndexGroupDict
        self.indexGroupMinLengthDict = indexGroupMinLengthDict

    def evaluateRegexGroup(self, hit) -> bool:
        """Evaluating a regular expression with groups

        Args:
            hit (_type_): 

        Returns:
            bool: 
        """
        result = True
        try:
            #Returns False unless all conditions are met.
            for index, length in self.indexGroupMinLengthDict.items():
                if len(hit.group(index)) < length:
                    result = False
            if result:
                for index, regexList in self.acceptRegexIndexGroupDict.items():
                    for regex in regexList:
                        if not re.search(regex, hit.group(index)):
                            result = False
                            break
                    if not result:
                        break
            if result:
                for index, regexList in self.rejectRegexIndexGroupDict.items():
                    for regex in regexList:
                        if re.search(regex, hit.group(index)):
                            result = False
                            break
                    if not result:
                        break
        except:
            result = False
        
        return result

    def isMatch(self, text: str) -> Dict[str, bool]:
        """Evaluates whether it matches the regular expression set in this class

        Args:
            text (str): 

        Returns:
            Dict[str, bool]: 
        """
        resultDict = {}
        hit = re.search(self.regex, text)
        if hit:
            if self.evaluateRegexGroup(hit):
                resultDict[self.regex] = True
            else:
                resultDict[self.regex] = False                    
        else:
            resultDict[self.regex] = False
        return resultDict
 
class DocumentFeatureCondition():
    """This class defines a concrete item of document feature.
    """
    regexIndexDict:Dict[int, List[DocumentFeatureRegexCondition]]
    regexCaptionDict:Dict[int, List[DocumentFeatureRegexCondition]]
    priority:int
    longProposition:bool
    pageDivisionTarget:bool
    isOnlyHeaderLine:bool = False