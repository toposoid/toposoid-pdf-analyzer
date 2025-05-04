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

from .PdfExtractorCommon import isHeaderOrFooter, getProtectPeriodIndexRegex
from functools import reduce
import re
import unicodedata


def getTableOfContents(documentInfoOnPage, headerRatio, footerRatio):
    """Check if there is something like a table of contents

    Args:
        documentInfoOnPage (_type_): _description_
        headerRatio (_type_): _description_
        footerRatio (_type_): _description_

    Returns:
        _type_: _description_
    """
    existToc = False
    for v in documentInfoOnPage.values():        
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]
        for  pdfDocumentBlock  in pdfDocumentBlocks:
            if pdfDocumentBlock.identifier.startswith("//Document/TOC"):
                existToc = True
                break
            else:
                textLine = pdfDocumentBlock.pdfTextLines[0]
                text = unicodedata.normalize('NFKC', textLine.text.strip().lower())                
                if textLine.fontSize >= pageInfo.mainFontSize and text in ["目次", "contents", "table of contents", "toc"]: 
                    existToc = True
                    break
                    
            
        if existToc:
            break

    if not existToc:
        return documentInfoOnPage

    foundTocHead = False
    isfinish = False
    convertDocumentInfoOnPage  = {}    
    prefixText = ""
    for pageId, v in documentInfoOnPage.items():
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]        
        tableOfContents = []        
        if isfinish: #When the table of contents range is exceeded, the table of contents analysis ends.
            convertDocumentInfoOnPage[pageId] = (pdfDocumentBlocks, pageInfo) 
        else:
            convertPdfDocumentBlocks = []                      
            for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):  
                #Exclude text that may be included in page headers and footers
                if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                    continue
                
                identifier = pdfDocumentBlock.identifier
                #If the identifier becomes a different path from the TOC, it may change to Reference.
                if identifier.startswith("//Document/TOC") or identifier.startswith("//Document/Reference") or re.search("^\/\/Document\/(Sect|L).*\/TOC", identifier) or re.search("^\/\/Document\/(Sect|L).*\/Reference", identifier) or re.search("^\/\/Document\/L\/LI.*\/Lbl", identifier):
                    foundTocHead = True 
                    textLine = prefixText + reduce(lambda x, y: x + y.text.replace("\n", ""), pdfDocumentBlock.pdfTextLines, "")  
                    if re.search("^" + getProtectPeriodIndexRegex() + "$", textLine.strip() + " "):
                        prefixText = textLine
                    else:                                            
                        tableOfContents.append(textLine)
                        prefixText = ""
                else:
                    convertPdfDocumentBlocks.append(pdfDocumentBlock)
                    if foundTocHead:
                        isfinish = True

            pageInfo.tableOfContents = tableOfContents
            convertDocumentInfoOnPage[pageId] = (convertPdfDocumentBlocks, pageInfo)
                    
    return convertDocumentInfoOnPage

