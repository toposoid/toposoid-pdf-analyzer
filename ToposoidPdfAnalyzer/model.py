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

from pydantic import BaseModel
from typing import List, Dict

class PdfPageInfo(BaseModel):
    """PDF page information object

    Args:
        BaseModel (_type_): 
    """
    pageId: int
    width: float
    height: float
    mainFontSize: int = -1
    pageBreakIdentifier: str = ""
    convergenceRadius: int = None
    representativePoints: List[int] = None
    references:List[str] = []
    tableOfContents:List[str] = []
    titleOfTopPage:str = ""
    headlines:List[str] = []

class PdfContentsCoodinate(BaseModel):
    """Coordinate objects for pdf content such as images and tables

    Args:
        BaseModel (_type_): 
    """
    x0: float
    y0: float
    x1: float
    y1: float

class PdfContentsInfo(BaseModel):
    """PDF content objects such as images and tables

    Args:
        BaseModel (_type_): _description_
    """
    id: str
    contentType: str #IMAGE OR TABLE OR CAPTION
    label: str
    path: str
    page: PdfPageInfo
    coodinate: PdfContentsCoodinate
    identifier: str
    metaList: List[str] = []

class PdfTextLine(BaseModel):
    """PDF content objects

    Args:
        BaseModel (_type_): 
    """
    text: str
    fontSize: float

class PdfDocumentBlock(BaseModel):
    """PDF document block objects

    Args:
        BaseModel (_type_): _description_
    """
    pdfTextLines: List[PdfTextLine]    
    x0: float
    y0: float
    x1: float
    y1: float
    pageId: int
    identifier: str = ""
    

class TextBlock(BaseModel):
    text: str
    pageId: int

class ParagraphInfo(BaseModel):
    totalText: str
    textBlocks: List[TextBlock]