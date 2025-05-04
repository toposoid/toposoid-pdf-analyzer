# toposoid-pdf-analyzer
This repository is a set of modules that parse PDFs within the Toposoid project. It is designed to work in conjunction with [toposoid-contents-admin-web](https://github.com/toposoid/toposoid-contents-admin-web). Toposoid is a knowledge base construction platform.(see Toposoid　Root Project)

## Requirements
* Python3.10
* Please see the note below

## Usage
```
#${path}:This Project Direcroty
pip install ${path}

import ToposoidPdfAnalyzer as tpa
```

## Note
* This library uses The PDF Extract API. In order to use The PDF Extract API, you need to create credentials. https://developer.adobe.com/document-services/apis/pdf-services/
After creating the credentials, please set the following environment variables.
TOPOSOID_PDF_SERVICES_CLIENT_ID
TOPOSOID_PDF_SERVICES_CLIENT_SECRET


## License
This program is offered under a commercial and under the AGPL license.
For commercial licensing, contact us at https://toposoid.com/contact.  
For AGPL licensing, see below.

AGPL licensing:
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

## Author
* Makoto Kubodera([Linked Ideal LLC.](https://linked-ideal.com/))

Thank you!
