# Repetitive Tasks for Milestones

#### Process all incomming submissions
Responsible: Rel-Mgmt

Please process all incomming submissions for ${Project} ${Epic}

#### Product build
Depends on: Process all incomming submissions
Responsible: Rel-Mgmt

Please make a product build of ${Project} ${Epic}

#### Test Product build
Responsible: qa
Depends on: Product build

Please test product build for ${Project} ${Epic}

#### Release Product build
Responsible: build
Depends on: Test Product build

Please release product build for ${Project} ${Epic}
