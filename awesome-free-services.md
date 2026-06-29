# Awesome Free Services for Developers

This is a list of software (SaaS, PaaS, IaaS, etc.) and other offerings with free developer tiers.

The scope of this list is limited to things that infrastructure developers (System Administrators, DevOps Practitioners, etc.) are likely to find useful.

> **NOTE:** This list is only for *as-a-Service* offerings, not for self-hosted software. To be eligible, a service must offer a **free tier**, not just a free trial. The free tier must be for at least a year if it is time-bucketed.

## Table of Contents

- [Major Cloud Providers' Always-Free Limits](#major-cloud-providers)
- [Cloud management solutions](#cloud-management-solutions)
- [Analytics, Events, and Statistics](#analytics-events-and-statistics)
- [APIs, Data and ML](#apis-data-and-ml)
- [Artifact Repos](#artifact-repos)
- [BaaS](#baas)
- [Low-code Platform](#low-code-platform)
- [CDN and Protection](#cdn-and-protection)
- [CI and CD](#ci-and-cd)
- [CMS](#cms)
- [Code Generation](#code-generation)
- [Code Quality](#code-quality)
- [Code Search and Browsing](#code-search-and-browsing)
- [Crash and Exception Handling](#crash-and-exception-handling)
- [Data Visualization on Maps](#data-visualization-on-maps)
- [Managed Data Services](#managed-data-services)
- [Design and UI](#design-and-ui)
- [Dev Blogging Sites](#dev-blogging-sites)
- [DNS](#dns)
- [Docker Related](#docker-related)
- [Domain](#domain)
- [Education and Career Development](#education-and-career-development)
- [Email](#email)
- [Feature Toggles Management Platforms](#feature-toggles-management-platforms)
- [Font](#font)
- [Forms](#forms)
- [Generative AI](#generative-ai)
- [IaaS](#iaas)
- [IDE and Code Editing](#ide-and-code-editing)
- [International Mobile Number Verification API and SDK](#international-mobile-number-verification-api-and-sdk)
- [Issue Tracking and Project Management](#issue-tracking-and-project-management)
- [Log Management](#log-management)
- [Mobile App Distribution and Feedback](#mobile-app-distribution-and-feedback)
- [Management Systems](#management-system)
- [Messaging and Streaming](#messaging-and-streaming)
- [Miscellaneous](#miscellaneous)
- [Monitoring](#monitoring)
- [PaaS](#paas)
- [Package Build System](#package-build-system)
- [Payment and Billing Integration](#payment-and-billing-integration)
- [Privacy Management](#privacy-management)
- [Screenshot APIs](#screenshot-apis)
- [Flutter Related and Building iOS Apps without Mac](#flutter-related-and-building-ios-apps-without-mac)
- [Search](#search)
- [Security and PKI](#security-and-pki)
- [Authentication, Authorization, and User Management](#authentication-authorization-and-user-management)
- [Source Code Repos](#source-code-repos)
- [Storage and Media Processing](#storage-and-media-processing)
- [Tunneling, WebRTC, Web Socket Servers and Other Routers](#tunneling-webrtc-web-socket-servers-and-other-routers)
- [Testing](#testing)
- [Tools for Teams and Collaboration](#tools-for-teams-and-collaboration)
- [Translation Management](#translation-management)
- [Visitor Session Recording](#visitor-session-recording)
- [Web Hosting](#web-hosting)
- [Commenting Platforms](#commenting-platforms)
- [Remote Desktop Tools](#remote-desktop-tools)
- [Other Free Resources](#other-free-resources)

---

## Major Cloud Providers

### Google Cloud Platform

- **App Engine** - 28 frontend instance hours per day, 9 backend instance hours per day.
- **Cloud Firestore** - 1GB storage, 50,000 reads, 20,000 writes, 20,000 deletes per day.
- **Compute Engine** - 1 non-preemptible e2-micro, 30GB HDD, 5GB snapshot storage (restricted to certain regions), 1 GB network egress from North America to all region destinations (excluding China and Australia) per month.
- **Cloud Storage** - 5GB, 1GB network egress.
- **Cloud Shell** - Web-based Linux shell/primary IDE with 5GB of persistent storage. 60 hours limit per week.
- **Cloud Pub/Sub** - 10GB of messages per month.
- **Cloud Functions** - 2 million invocations per month (includes both background and HTTP invocations).
- **Cloud Run** - 2 million requests per month, 360,000 GB-seconds memory, 180,000 vCPU-seconds of compute time, 1 GB network egress from North America per month.
- **Google Kubernetes Engine** - No cluster management fee for one zonal cluster. Each user node is charged at standard Compute Engine pricing.
- **BigQuery** - 1 TB of querying per month, 10 GB of storage each month.
- **Cloud Build** - 120 build-minutes per day.
- **Google Colab** - Free Jupyter Notebooks development environment.
- **Kaggle** - Jupyter Notebooks with 4 CPU cores and 30 GB RAM. With phone verification, GPU/TPU options available with weekly usage limits.
- **Google Gemini API** - Free access to Gemini 1.5 Pro and Gemini 1.5 Flash models. 15 requests per minute, 1,500 requests per day, 1 million tokens per minute.
- Full, detailed list - https://cloud.google.com/free

### Amazon Web Services

- **CloudFront** - 1TB egress per month and 2M Function invocations per month.
- **CloudWatch** - 10 custom metrics and 10 alarms.
- **CodeBuild** - 100min of build time per month.
- **CodeCommit** - 5 active users, 50GB storage, and 10000 requests per month.
- **CodePipeline** - 1 active pipeline per month.
- **DynamoDB** - 25GB NoSQL DB.
- **EC2** - 750 hours per month of t2.micro or t3.micro (12mo). 100GB egress per month.
- **EBS** - 30GB per month of General Purpose (SSD) or Magnetic (12mo).
- **Elastic Load Balancing** - 750 hours per month (12mo).
- **RDS** - 750 hours per month of db.t2.micro, db.t3.micro, or db.t4g.micro, 20GB SSD storage, 20GB storage backups (12mo).
- **S3** - 5GB Standard object storage, 20K Get requests and 2K Put requests (12mo).
- **Glacier** - 10GB long-term object storage.
- **Lambda** - 1 million requests per month.
- **SNS** - 1 million publishes per month.
- **SES** - 3,000 messages per month (12mo).
- **SQS** - 1 million messaging queue requests.
- Full, detailed list - https://aws.amazon.com/free/

### Microsoft Azure

- **Virtual Machines** - 1 B1S Linux VM, 1 B1S Windows VM (12mo).
- **App Service** - 10 web, mobile, or API apps (60 CPU minutes/day).
- **Functions** - 1 million requests per month.
- **DevTest Labs** - Fast, easy, and lean dev-test environments.
- **Active Directory** - 500,000 objects.
- **Active Directory B2C** - 50,000 monthly stored users.
- **Azure DevOps** - 5 active users, unlimited private Git repos.
- **Azure Pipelines** - 10 free parallel jobs with unlimited minutes for open source (Linux, macOS, Windows).
- **Microsoft IoT Hub** - 8,000 messages per day.
- **Load Balancer** - 1 free public load-balanced IP (VIP).
- **Notification Hubs** - 1 million push notifications.
- **Bandwidth** - 15GB Inbound (12mo) & 5GB egress per month.
- **Cosmos DB** - 25GB storage and 1000 RUs of provisioned throughput.
- **Static Web Apps** - Build, deploy, and host static apps and serverless functions with free SSL, auth, and custom domains.
- **Storage** - 5GB LRS File or Blob storage (12mo).
- **Cognitive Services** - AI/ML APIs with free tier including limited transactions.
- **Cognitive Search** - AI-based search and indexation service, free for 10,000 documents.
- **Azure Kubernetes Service** - Managed Kubernetes service, free cluster management.
- **Event Grid** - 100K ops/month.
- Full, detailed list - https://azure.microsoft.com/free/

### Oracle Cloud

- **Compute** - 2 AMD-based Compute VMs (1/8 OCPU, 1 GB memory each); 2 Arm-based Ampere A1 cores and 12 GB of memory. Instances reclaimed when deemed idle.
- **Block Volume** - 2 volumes, 200 GB total.
- **Object Storage** - 10 GB.
- **Load balancer** - 1 instance with 10 Mbps.
- **Databases** - 2 DBs, 20 GB each.
- **Monitoring** - 500 million ingestion data points, 1 billion retrieval datapoints.
- **Bandwidth** - 10 TB egress per month.
- **Public IP** - 2 IPv4 for VMs, 1 IPv4 for load balancer.
- **Notifications** - 1 million delivery options per month, 1000 emails sent per month.
- Full, detailed list - https://www.oracle.com/cloud/free/

### IBM Cloud

- **Cloudant database** - 1 GB of data storage.
- **Db2 database** - 100MB of data storage.
- **API Connect** - 50,000 API calls per month.
- **Availability Monitoring** - 3 million data points per month.
- **Log Analysis** - 500MB of daily log.
- Full, detailed list - https://www.ibm.com/cloud/free/

### Cloudflare

- **Application Services** - Free DNS for unlimited domains, DDoS Protection, CDN with free SSL, Firewall/page rules, WAF, Bot Mitigation, Rate Limiting (1 rule per domain), Analytics, Email forwarding.
- **Zero Trust & SASE** - Up to 50 Users, 24 hours of activity logging, 3 network locations.
- **Cloudflare Tunnel** - Expose locally running HTTP port over a tunnel to a random subdomain on trycloudflare.com (Quick Tunnels), no account required.
- **Workers** - Deploy serverless code free - 100k daily requests.
- **Workers KV** - 100k read requests/day, 1000 write/delete/list requests/day, 1 GB stored data.
- **R2** - 10 GB per month, 1 million Class A operations, 10 million Class B operations per month.
- **D1** - 5 million rows read per day, 100k rows written per day, 1 GB storage.
- **Pages** - 500 monthly builds, 100 custom domains, Integrated SSL, unlimited preview deployments.
- **Queues** - 1 million operations per month.
- **TURN** - 1TB of free (outgoing) traffic per month.

### Zoho

Started as an e-mail provider but now provides a suite of services, some of which have free plans:

- **Catalyst by Zoho** - PaaS/full-stack cloud platform with a generous free tier.
- **Email** - Free for 5 users. 5GB/user & 25 MB attachment limit, one domain.
- **Zoho Assist** - 1 concurrent remote support license, access to 5 unattended computer licenses.
- **Sprints** - Free for 5 users, 5 Projects & 500MB storage.
- **Docs** - Free for 5 users with 1 GB upload limit & 5GB storage.
- **Projects** - Free for 3 users, 2 projects & 10 MB attachment limit.
- **Connect** - Team collaboration free for 25 users with 3 groups, 3 custom apps, 3 Boards, 3 Manuals, 10 Integrations.
- **Meeting** - Meetings with up to 3 participants & 10 Webinar attendees.
- **Vault** - Password Management for Individuals.
- **Showtime** - Meeting/training software for a remote session of up to 5 attendees.
- **Notebook** - A free alternative to Evernote.
- **Wiki** - Free for 3 users with 50 MB storage, unlimited pages, zip backups, RSS & Atom feed.
- **Subscriptions** - Recurring Billing free for 20 customers/subscriptions & 1 user.
- **Checkout** - Product Billing with 3 pages & up to 50 payments.
- **Desk** - Customer Support with 3 agents, private knowledge base, email tickets.
- **Cliq** - Team chat with 100 GB storage, unlimited users, 100 users per channel & SSO.
- **Campaigns** - Email Marketing.
- **Forms** - Form Creator.
- **Sign** - Paperless Signatures.
- **Surveys** - Online Surveys.
- **Bookings** - Appointment Scheduling.

[⬆️ Back to Top](#table-of-contents)

## Cloud management solutions

- **Brainboard** - Collaborative solution to visually build and manage cloud infrastructures end-to-end.
- **Cloud 66** - Free for personal projects (one deployment server, one static site).
- **deployment.io** - Automate deployments on AWS. Free tier: single user, unlimited static sites, web services, and environments; 10 job executions/month with previews and auto-deploys.
- **Pulumi** - Modern infrastructure as code platform using familiar programming languages.
- **scalr.com** - Terraform Automation and Collaboration (TACO) product. Full Terraform CLI support, OPA integration. Up to 50 runs/month free.

[⬆️ Back to Top](#table-of-contents)

## Source Code Repos

- **Bitbucket** - Unlimited public and private Git repos for up to 5 users with Pipelines for CI/CD.
- **Codeberg** - Unlimited public and private Git repos for free and open-source projects. Powered by Forgejo. Pages, CI/CD, Translate, Package/Container hosting, Project management, Issue Tracking.
- **framagit.org** - Software forge of Framasoft based on GitLab; includes CI, Static Pages, Project pages, Issue tracking.
- **GitGud** - Unlimited private and public repositories. Powered by GitLab & Sapphire. Includes CI/CD, Static Hosting, Container Registry, Project Management, Issue Tracking.
- **GitHub** - Unlimited public and private repositories with unlimited collaborators. Includes CI/CD, Codespaces, Static Hosting, Package/Container hosting, Project management, Copilot.
- **gitlab.com** - Unlimited public and private Git repos with up to 5 collaborators. Includes CI/CD, Static Hosting, Container Registry, Project Management, Issue Tracking.
- **heptapod.net** - Friendly fork of GitLab Community Edition with support for Mercurial.
- **pijul.com** - Unlimited free and open source distributed version control system based on a sound theory of patches.
- **projectlocker.com** - One free private project (Git and Subversion) with 50 MB of space.
- **RocketGit** - Repository Hosting based on Git. Unlimited Public and private repositories.
- **savannah.gnu.org** - Collaborative software development management system for GNU Projects.
- **savannah.nongnu.org** - Collaborative software development management system for non-GNU projects.

[⬆️ Back to Top](#table-of-contents)

## APIs, Data, and ML

- **Abstract API** - API suite for IP geolocation, phone number validation, email validation, etc.
- **Apify** - Web scraping and automation platform. Free plan with $5 platform credits monthly.
- **APITemplate.io** - Auto-generate images and PDF documents via API. Free: 50 images/month and 3 templates.
- **APIVerve** - 120+ APIs. Free plan: up to 50 API Tokens per month.
- **Arize AI** - ML observability for model monitoring. Free up to two models.
- **Beeceptor** - No-code platform for mocking and debugging APIs (REST, SOAP, gRPC, GraphQL). Free: 50 requests/day.
- **BigDataCloud** - Fast, accurate, free APIs for IP Geolocation, Reverse Geocoding, Networking Insights, and more.
- **Browse AI** - Extract and monitor data on the web. 1k credits/month free.
- **BrowserCat** - Headless browser API for automation, scraping, AI agent web access. Free: 1k requests/month.
- **Calendarific** - Public holiday API for 200+ countries. Free: 500 calls/month.
- **Canopy** - GraphQL API for Amazon product, search, and category data. Free: 100 calls/month.
- **CarAPI.dev** - Automotive data API with VIN decoding, valuation, and more. Free: 100 requests/month.
- **Cloudmersive** - Utility API platform with 600 calls/month.
- **CometML** - MLOps platform for experiment tracking. Free for individuals and academics.
- **Commerce Layer** - Composable commerce API. Developer plan: 100 orders/month, up to 1,000 SKUs.
- **Composio** - Integration platform for AI Agents and LLMs (200+ tools).
- **Conversion Tools** - Online File Converter. Free tier: 20MB max, 30/day, 300/month.
- **Cube** - Access data from modern data stores. Free tier: 1,000 queries/day.
- **CurlHub** - Proxy service for inspecting and debugging API calls. Free: 10,000 requests/month.
- **CurrencyScoop** - Realtime currency data API. Free: 5,000 calls/month.
- **CustomJS** - HTML to PDF or PDF to PNG/Text & PDF merging/extraction APIs. Free: 600 calls/month.
- **Datalore** - Python notebooks by JetBrains. 10 GB storage and 120 hours runtime/month.
- **DB Designer** - Cloud-based DB schema design. Free: 2 models and 10 tables per model.
- **DB-IP** - Free IP geolocation API with 1k requests per IP per day.
- **Deepnote** - Data science notebook. Free tier: unlimited personal projects, 5GB RAM / 2vCPU machines.
- **Disease.sh** - Free API providing accurate Covid-19 data.
- **drawDB** - Free and open-source online database diagram editor, no signup required.
- **Firecrawl** - Crawls websites into clean LLM-ready markdown or structured data. Free: 1,000 credits/month.
- **FraudLabs Pro** - Screen order transactions for fraud. Free Micro plan: 500 transactions/month.
- **FreeIPAPI** - Free, fast IP Geolocation API (JSON).
- **Geolocated.io** - IP Geolocation API. Free: 2,000 requests/day.
- **Hex** - Collaborative data platform for notebooks and data apps. Free community tier with up to 5 projects.
- **Hook0** - Open-source Webhooks-as-a-service. Free: up to 100 events/day, 7 days retention.
- **Hoppscotch** - Free, fast, and beautiful API request builder.
- **huggingface.co** - Build, train, and deploy NLP models. Free up to 30k input characters/mo.
- **Insomnia** - Open-source API client supporting REST and GraphQL.
- **IP Geolocation API (ipwho.org)** - 2,000 free requests/day.
- **ip-api** - IP Geolocation API, free for non-commercial use, 45 req/minute.
- **IP2Location.io** - IP geolocation API. Free: 50k credits/month.
- **ipapi.is** - IP Address API with hosting detection. Free: 1000 lookups without signup.
- **ipapi** - Geolocation API on AWS. Free tier: 30k lookups/month (1k/day).
- **IPinfo** - IP address data API. Free up to 50k/month.
- **IPLocate** - IP Geolocation API, free up to 1,000 requests/day.
- **JSON IP** - Returns the Public IP address of the client. Unlimited requests.
- **JSON2Video** - A video editing API to automate video creation.
- **News API** - Search news on the web; 100 queries/day free.
- **numlookupapi.com** - Free phone number validation API - 100 free requests/month.
- **OCR.Space** - OCR API. 25,000 requests/month free, 1MB file size limit.
- **Parseur** - 20 free pages/month: Extract data from PDFs, emails.
- **Pixela** - Free daystream database service. Visualization with heat maps and line graphs.
- **Postman** - API development collaboration platform. Free forever with limits.
- **SerpApi** - Real-time search engine scraping API. Free: 100 calls/month.
- **Svix** - Webhooks as a Service. Up to 50,000 messages/month free.
- **Tavily AI** - API for online search and research. 1000 requests/month free.
- **TinyMCE** - Rich text editing API. Core features free for unlimited usage.
- **Treblle** - API log aggregation, observability, docs, debugging. Up to 250k requests/month free.
- **WeatherXu** - Global weather data API. Free tier: 10,000 API calls/month.
- **WebScraping.AI** - Simple Web Scraping API with parsing and proxies. 2,000 free API calls/month.
- **Weights & Biases** - MLOps platform. Free tier for personal projects, 100 GB storage.
- **wolfram.com** - Built-in knowledge-based algorithms in the cloud.
- **wrapapi.com** - Turn any website into a parameterized API. 30k API calls/month.
- **Zenscrape** - Web scraping API with headless browsers. 1000 free API calls/month.
- **Zipcodebase** - Free Zip Code API. 5,000 requests/month.
- **Zipcodestack** - Free Zip Code API and Postal Code Validation. 10,000 requests/month.
- **Zuplo** - Free API Management platform. Up to 10 projects, 1M monthly requests, 10GB egress.

[⬆️ Back to Top](#table-of-contents)

## Artifact Repos

- **Gemfury** - Private and public artifact repos for Maven, PyPi, NPM, Go Module, Nuget, APT, RPM. Free for public projects.
- **jitpack.io** - Maven repository for JVM and Android projects on GitHub, free for public projects.
- **paperspace** - Build & scale AI models. Free plan: public projects, 5Gb storage, basic instances.
- **RepoFlow** - Package management (npm, PyPI, Docker, Go, Helm). Free: 10GB storage, 100 packages, unlimited users.
- **RepoForge** - Private cloud-hosted repository for Python, Debian, NPM packages and Docker registries. Free for open source/public projects.
- **repsy.io** - 1 GB Free private/public Maven Repository.

[⬆️ Back to Top](#table-of-contents)

## BaaS

- **Activepieces** - Build automation flows to connect apps. Free up to 5,000 tasks/month.
- **back4app.com** - Easy-to-use, flexible, scalable backend based on Parse Platform.
- **backendless.com** - Mobile and Web BaaS. 1 GB file storage, 50,000 push notifications/month, 1000 data objects.
- **connectycube.com** - Unlimited chat messages, p2p voice & video calls, files, push notifications. Free for apps up to 1000 users.
- **convex.dev** - Reactive backend as a service. Free for small projects - up to 1M records, 5M monthly function calls.
- **getstream.io** - Build scalable In-App Chat, Messaging, Video and Feeds.
- **IFTTT** - Automate your favorite apps and devices. Free 2 Applets.
- **Integrately** - Automate tasks. Free 100 Tasks, 15 minute interval.
- **LeanCloud** - Mobile backend. 1GB data storage, 256MB instance, 3K API requests/day, 10K pushes/day.
- **nhost.io** - Serverless backend. Free: PostgreSQL, GraphQL (Hasura), Auth, Storage, Serverless Functions.
- **onesignal.com** - Unlimited free push notifications. 10,000 email sends/month.
- **Supabase** - Open Source Firebase Alternative. Free: Auth, Realtime Database, Object Storage.
- **tyk.io** - API management with auth, quotas, monitoring, analytics. Free cloud offering.
- **zapier.com** - Connect apps to automate tasks. 5 zaps, 100 tasks/month.

[⬆️ Back to Top](#table-of-contents)

## Low-code Platform

- **appsmith** - Low code project to build admin panels, internal tools, dashboards. 15+ databases & any API.
- **BudiBase** - Open-source low-code platform for internal apps. Supports PostgreSQL, MySQL, MSSQL, MongoDB, Rest API.
- **Clappia** - Low-code platform for building business process apps with a drag-and-drop interface.
- **lil'bots** - Write and run scripts online with free built-in APIs. Free: 10,000 execution credits/month.
- **manubes** - No-code cloud platform focused on industrial production management. Free for 1 user with 1 million workflow activities/month.
- **Mendix** - Rapid Application Development for Enterprises. Unlimited sandbox environments, 0.5 GB storage, 1 GB RAM per app.
- **outsystems.com** - Enterprise web development PaaS. Free "personal environment" with unlimited code and up to 1 GB database.
- **ReTool** - Low-code platform for internal apps. Free tier: up to 5 users/month, unlimited apps.
- **ToolJet** - Extensible low-code framework for business applications.
- **UI Bakery** - Low-code platform for custom web applications. Free for up to 5 users.

[⬆️ Back to Top](#table-of-contents)

## CDN and Protection

- **bootstrapcdn.com** - CDN for bootstrap, bootswatch and fontawesome.io.
- **CacheFly** - Up to 5 TB/month of Free CDN traffic, 1 Domain and Universal SSL.
- **cdnjs.com** - Free and open-source CDN service, powered by Cloudflare.
- **developers.google.com** - Google Hosted Libraries CDN for popular Open Source JavaScript libraries.
- **Gcore** - Global CDN, 1 TB and 1 million requests/month free plus free DNS hosting.
- **jsdelivr.com** - A free, fast, and reliable open-source CDN. Supports npm, GitHub, WordPress, Deno.
- **Microsoft Ajax** - Hosts popular third-party JavaScript libraries such as jQuery.
- **Namecheap Supersonic** - Free DDoS protection.
- **ovh.ie** - Free DDoS protection and SSL certificate.
- **raw.githack.com** - A modern replacement of rawgit.com, hosts files using Cloudflare.
- **Skypack** - 100% Native ES Module JavaScript CDN. Free for 1 million requests per domain per month.
- **statically.io** - CDN for Git repos, WordPress assets, and images.
- **Stellate** - Blazing-fast CDN for your GraphQL API, free for two services.
- **UNPKG** - CDN for everything on npm.
- **weserv** - An image cache & resize service.

[⬆️ Back to Top](#table-of-contents)

## CI and CD

- **appcircle.io** - Mobile DevOps platform. Free: 30 min max build time, 20 monthly builds, 1 concurrent build.
- **appveyor.com** - CD service for Windows, free for Open Source.
- **bitrise.io** - CI/CD for mobile apps. 200 free builds/month, 10 min build time, 2 team members.
- **buddy.works** - CI/CD with 5 free projects and 1 concurrent run (120 executions/month).
- **Buildkite** - CI Pipelines free for 3 users and 5k job minutes/month.
- **bytebase.com** - Database CI/CD and DevOps. Free under 20 users and 10 database instances.
- **CircleCI** - Free for up to 6000 minutes/month, 30 parallel jobs in private projects, up to 80,000 build minutes for Open Source.
- **cirun.io** - Free for public GitHub repositories.
- **codemagic.io** - Free 500 build minutes/month.
- **deployhq.com** - 1 project with 10 daily deployments (30 build minutes/month).
- **LocalOps** - Deploy on AWS/GCP/Azure. Free plan: 1 user and 1 app environment.
- **Make** - Workflow automation tool. Free tier: 100 Mb, 1000 Operations, 15 min interval.
- **Mergify** - Workflow automation and merge queue for GitHub. Free for public GitHub repositories.
- **Nx Cloud** - Speeds up monorepos on CI. Free plan for up to 30 contributors, 150k credits.
- **Shipfox** - Run GitHub actions 2x faster. 3,000 build minutes free each month.
- **Spacelift** - Management platform for IaC. Free: up to 200 minutes/month.
- **Squash Labs** - Creates a VM for each branch. Unlimited public & private repos, up to 2 GB VM Sizes.
- **Terramate** - Orchestration and management platform for IaC. Free up to 2 users.
- **Terrateam** - GitOps-first Terraform automation. Free for up to 3 users.

[⬆️ Back to Top](#table-of-contents)

## CMS

- **Contentful** - Headless CMS. Free Community space: 5 users, 25K records, 48 Content Types, 2 locales.
- **Cosmic** - Headless CMS and API toolkit. Free personal plans for developers.
- **Crystallize** - Headless PIM with ecommerce support. Free: unlimited users, 1000 catalog items, 5 GB/month bandwidth, 25k/month API calls.
- **DatoCMS** - GraphQL-based CMS. Free tier: 100k/month calls.
- **Hygraph** - GraphQL native Headless CMS. Free tier for small projects.
- **Prismic** - Headless CMS. Community Plan: unlimited API calls, documents, custom types, assets, and locales to one user.
- **Sanity.io** - Platform for structured content. Unlimited projects, 3 non-admin users, 500K API CDN requests, 10GB bandwidth, 5GB assets per project.
- **Solo** - Free AI website creator from Mozilla. Free custom domain.
- **Squidex** - API / GraphQL first, open source, event sourcing. Free tier for small projects.
- **Storyblok** - Headless CMS for developers and marketers. Community tier with many features and 250GB Traffic/month.
- **TinaCMS** - Open source Git-backed headless CMS (Markdown, MDX, JSON). Free with 2 users.
- **WPJack** - Set up WordPress on any cloud. Free: 1 server, 2 sites, free SSL, unlimited cron jobs.

[⬆️ Back to Top](#table-of-contents)

## Code Generation

- **Appinvento** - Free no-code app builder. Free plan: three projects and five tables.
- **DhiWise** - Converts Figma designs into Flutter and React applications.
- **Karbon Sites** - AI-powered site builder generating frontend code. Free tier: 5 generations/month.
- **Metalama** - C#-specific tool generating boilerplate code during compilation. Free tier: up to three aspects.
- **Supermaven** - High-speed AI code completion plugin. Free tier: unlimited inline completions.
- **v0.dev** - Generates copy-and-paste React code using shadcn/ui and Tailwind CSS. 1,200 starting credits, 200 free monthly.

[⬆️ Back to Top](#table-of-contents)

## Code Quality

- **beanstalkapp.com** - Workflow to write, review, and deploy code. Free for 1 user, 1 repository, 100 MB.
- **codacy.com** - Automated code reviews. Free for unlimited public and private repositories.
- **Codeac.io** - Automated IaC review tool for DevOps. Free for open-source.
- **codecov.io** - Code coverage tool. Free for Open Source and one free private repo.
- **CodeFactor** - Automated Code Review for Git. Free: unlimited public repositories and one private repo.
- **coderabbit.ai** - AI-powered code review. Free forever for open source projects.
- **CodSpeed** - Automate performance tracking in CI pipelines. Free forever for Open Source.
- **coveralls.io** - Display test coverage reports, free for Open Source.
- **deepscan.io** - Advanced static analysis for JavaScript, free for Open Source.
- **DeepSource** - Continuously analyzes source code changes. Integrates with GitHub, GitLab, Bitbucket.
- **DiffText** - Instantly find the differences between two blocks of code. Free.
- **gerrithub.io** - Gerrit code review for GitHub repositories for free.
- **goreportcard.com** - Code Quality for Go projects, free for Open Source.
- **houndci.com** - Comments on GitHub commits about code quality, free for Open Source.
- **reviewable.io** - Code review for GitHub repositories, free for public or personal repos.
- **scan.coverity.com** - Static code analysis for Java, C/C++, C# and JavaScript, free for Open Source.
- **scrutinizer-ci.com** - Continuous inspection platform, free for Open Source.
- **semanticdiff.com** - Programming language aware diff for GitHub, free for public repositories.
- **shields.io** - Quality metadata badges for open source projects.
- **sonarcloud.io** - Automated source code analysis for many languages, free for Open Source.

[⬆️ Back to Top](#table-of-contents)

## Code Search and Browsing

- **CodeKeep** - Google Keep for Code Snippets. Organize, discover, and share code snippets.
- **libraries.io** - Search and dependency update notifications for 32 package managers, free for open source.
- **Namae** - Search various websites for the availability of your project name.
- **tickgit.com** - Surfaces TODO comments to identify areas of code worth improving.

[⬆️ Back to Top](#table-of-contents)

## CI and CD

See [CI and CD](#ci-and-cd) above.

## Testing

- **Appetize** - Cloud-based Android/iOS emulator in your browser. Free: 2 concurrent sessions, 30 min/month.
- **Argos** - Open Source visual testing. Unlimited projects, 5,000 screenshots/month. Free for open-source.
- **Bencher** - Continuous benchmarking tool suite. Free for all public projects.
- **BugBug** - Lightweight test automation for web apps. Run unlimited tests on your own computer free.
- **checkbot.io** - Browser extension testing 50+ SEO, speed and security best practices. Free tier for smaller websites.
- **Checkly** - Code-first synthetic monitoring. Generous free tier for devs.
- **CORS-Tester** - Check if an API is CORS-enabled for a given domain.
- **cypress.io** - Fast, easy, reliable browser testing. Test Runner free and open-source.
- **gridlastic.com** - Selenium Grid testing. Free: up to 4 simultaneous nodes/10 grid starts/4,000 test minutes/month.
- **katalon.com** - Testing platform including Katalon Studio, TestOps, TestCloud, and Katalon Recorder.
- **Keploy** - Functional testing toolkit. Free for Open Source projects.
- **loadmill.com** - Automatically create API and load tests. Free: 50 concurrent users for up to 60 minutes monthly.
- **lost-pixel.com** - Visual regression testing. Free for open-source, 7,000 snapshots/month.
- **percy.io** - Add visual testing to any web app. 5,000 snapshots/month.
- **qase.io** - Test management for Dev and QA teams. Free tier: 500MB attachments, up to 3 users.
- **Repeato** - No-code mobile app test automation. Free plan: 10 tests for iOS and 10 for Android.
- **Requestly** - Open-source Chrome Extension to Intercept, Redirect and Mock HTTP Requests. Up to 10 rules free.
- **testingbot.com** - Selenium Browser and Device Testing, free for Open Source.
- **Testspace.com** - Dashboard for publishing automated test results. Free for Open Source, 450 monthly results.
- **UseWebhook.com** - Capture and inspect webhooks from your browser. Free.
- **webhook.site** - Verify webhooks, HTTP requests, or emails with a custom URL. Free.
- **websitepulse.com** - Various free network and server tools.

[⬆️ Back to Top](#table-of-contents)

## Security and PKI

- **aikido.dev** - All-in-one appsec platform (SCA, SAST, CSPM, DAST, Secrets, IaC, etc.). Free: 2 users, 10 repos.
- **CertKit** - Manage SSL Certificate issuance, renewal, monitoring. Free for 3 certificates and 1 user.
- **Corgea** - Autonomous security platform that finds, validates and fixes insecure code. Free: 1 user and 2 repos.
- **CyberChef** - Web app for analyzing and decoding/encoding data. All features free, open source.
- **Datree** - Open Source CLI tool to prevent Kubernetes misconfigurations.
- **Dependabot** - Automated dependency updates for many ecosystems.
- **Doppler** - Universal Secrets Manager. Free for 5 users with basic access controls.
- **Dotenv** - Sync your .env files securely. Free for up to 3 teammates.
- **GitGuardian** - Automated secrets detection and remediation. Free for individuals and teams of 25 or less.
- **HasMySecretLeaked** - Search exposed secrets in public GitHub repos. Free.
- **Have I been pwned?** - REST API for fetching information on breaches.
- **hostedscan.com** - Online vulnerability scanner. 10 free scans/month.
- **Infisical** - Open source platform to manage developer secrets. Free for up to 5 developers.
- **Internet.nl** - Test for modern Internet Standards (IPv6, DNSSEC, HTTPS, DMARC, etc.).
- **letsencrypt.org** - Free SSL Certificate Authority trusted by all major browsers.
- **Mozilla Observatory** - Find and fix security vulnerabilities in your site.
- **Socket** - Free supply chain security for individual developers and open source projects.
- **ssllabs.com** - Intense analysis of the configuration of any SSL web server.
- **Sucuri SiteCheck** - Free website security check and malware scanner.
- **Virgil Security** - Tools for end-to-end encryption. Free for applications with up to 250 users.

[⬆️ Back to Top](#table-of-contents)

## Authentication, Authorization, and User Management

- **Aserto** - Fine-grained authorization as a service. Free up to 1000 MAUs and 100 authorizer instances.
- **asgardeo.io** - SSO, MFA, passwordless auth. Free up to 1000 MAUs and 5 identity providers.
- **Auth0** - Hosted SSO. Free plan: 25,000 MAUs, unlimited Social Connections, custom domain.
- **Authgear** - Passwordless, OTPs, 2FA, SSO. Free up to 5000 MAUs.
- **Authress** - Authentication and access control. First 1000 API calls free.
- **Cerbos Hub** - Authorization management system. Free up to 100 monthly active principals.
- **Clerk** - User management, authentication, 2FA/MFA. Free plan: 50,000 MRU per app.
- **Cloud-IAM** - Keycloak Identity and Access Management as a Service. Free up to 100 users and 1 realm.
- **Descope** - Customizable AuthN flows. Free: 7,500 active users/month, 50 tenants.
- **duo.com** - Two-factor authentication. Free for 10 users, all authentication methods.
- **Kinde** - Authentication. 7,500 free MAU.
- **Logto** - Develop, secure, and manage user identities. Free for up to 5,000 MAUs.
- **Okta** - User management, authentication, authorization. Free for up to 100 monthly active users.
- **Ory** - AuthN/AuthZ/OAuth2.0 managed security platform. Free: 200 daily active users, 25k/mo permission checks.
- **Permit.io** - Authorization-as-a-service (RBAC, ABAC, ReBAC). 1000 Monthly Active User free tier.
- **Stack Auth** - Open-source authentication. Managed SaaS with 10k free Monthly Active Users.
- **Stytch** - APIs and SDKs for authentication and fraud prevention. Free: 10,000 MAUs.
- **SuperTokens** - Open source user authentication. Free for up to 5000 MAUs.
- **WorkOS** - Free user management and authentication for up to 1 Million MAUs.
- **ZITADEL Cloud** - Turnkey user and access management. Free for up to 25,000 authenticated requests.

[⬆️ Back to Top](#table-of-contents)

## Mobile App Distribution and Feedback

- **Appho.st** - Mobile app hosting. Free: 5 apps, 50 monthly downloads, 100 MB max file size.
- **Diawi** - Deploy iOS & Android apps directly to devices. Free plan: 1-day expiration, 10 installations.
- **GetUpdraft** - Distribute mobile apps for testing. Free: 1 app project, 3 versions, 500 MB storage, 100 installs/month.
- **InstallOnAir** - Distribute iOS & Android apps over the air. Free plan: unlimited uploads, private links.
- **Loadly** - iOS & Android beta apps distribution. Free with unlimited downloads and uploads.

[⬆️ Back to Top](#table-of-contents)

## Management System

- **bitnami.com** - Deploy prepared apps on IaaS. Management of 1 AWS micro instance free.
- **Esper** - MDM and MAM for Android Devices. 100 devices free with 1 user license and 25 MB Application Storage.
- **jamf.com** - Device management for iPads, iPhones, and Macs, 3 devices free.
- **Miradore** - Device Management service. Secure unlimited devices for free with basic features.
- **ploi.io** - Server management tool. Free for one server.
- **runcloud.io** - Server management focused on PHP projects. Free for up to 1 server.
- **serveravatar.com** - Manage and monitor PHP-based web servers. Free for one server.
- **xcloud.host** - Server management and deployment platform. Free tier for one server.

[⬆️ Back to Top](#table-of-contents)

## Messaging and Streaming

- **Ably** - Realtime messaging service. Free: 3m messages/month, 100 peak connections, 100 peak channels.
- **cloudamqp.com** - RabbitMQ as a Service. Little Lemur plan: max 1 million messages/month.
- **courier.com** - Single API for push, in-app, email, chat, SMS. Free: 10,000 messages/mo.
- **EMQX Serverless** - Serverless MQTT broker. 1M session minutes/month free forever.
- **Engage** - Customer Engagement and Automation Tool. Free for up to 1,000 active users/month.
- **engagespot.co** - Multi-channel notification infrastructure. Free: 10,000 messages/mo.
- **HiveMQ** - Cloud Native IoT Messaging Broker. Free to connect up to 100 devices forever.
- **httpSMS** - Use your Android phone as an SMS Gateway. Free to send and receive up to 200 messages/month.
- **knock.app** - Notifications infrastructure. Free: 10,000 messages/mo.
- **Novu.co** - Open-source notification infrastructure. Free: 30,000 notifications/month, 90 days retention.
- **Pingram.io** - Communication infrastructure. Free: 100 SMS and calls, 3000 Emails, Push, Slack, etc.
- **pubnub.com** - Messaging at 1 million transactions each month.
- **pusher.com** - Realtime messaging. Free for up to 100 simultaneous connections and 200,000 messages/day.
- **scaledrone.com** - Realtime messaging. Free for up to 20 simultaneous connections and 100,000 events/day.
- **synadia.com** - NATS.io as a service. Free forever with 50 active connections and 5GB of data per month.
- **webpushr** - Web Push Notifications. Free for up to 10k subscribers, unlimited push notifications.

[⬆️ Back to Top](#table-of-contents)

## Log Management

- **bugfender.com** - Free up to 100k log lines/day with 24 hours retention.
- **log.dog** - Remote debugging/logging SDK (iOS and Android). Free for up to 100MB of logs every month.
- **logflare.app** - Free for up to 12,960,000 entries per app per month, 3 days retention.
- **logtail.com** - ClickHouse-based SQL-compatible log management. Free up to 1 GB/month, 3 days retention.
- **ManageEngine Log360 Cloud** - Log Management service. Free: 50 GB storage, 15 days retention, 7 days search.
- **openobserve.ai** - 200 GB Ingestion/month free, 15 Days Retention.

[⬆️ Back to Top](#table-of-contents)

## Translation Management

- **AutoLocalise.com** - Instantly localize without managing translation files. Free: 10,000 characters/month.
- **crowdin.com** - Unlimited projects, strings, and collaborators for Open Source.
- **Lingo.dev** - Open-source AI-powered CLI for web & mobile localization. 10,000 free words every month.
- **lingohub.com** - Free up to 3 users, always free for Open Source.
- **localazy.com** - Free for 1000 source language strings, unlimited languages and contributors.
- **localizely.com** - Free for Open Source.
- **POEditor** - Free up to 1000 strings.
- **SimpleLocalize** - Free up to 100 translation keys, unlimited strings and languages.
- **Texterify** - Free for a single user.
- **Tolgee** - Free SaaS offering, forever-free self-hosted version.
- **transifex.com** - Free for Open Source.

[⬆️ Back to Top](#table-of-contents)

## Monitoring

- **assertible.com** - Automated API testing and monitoring. Free plans for teams and individuals.
- **Better Stack** - Uptime monitoring, incident management, on-call, status pages. Free: 10 monitors.
- **bleemeo.com** - Free for 3 servers, 5 uptime monitors, unlimited users, dashboards, alerting rules.
- **checklyhq.com** - Open source E2E / Synthetic monitoring. Free plan with 10k API & network check runs.
- **cronitor.io** - Performance insights and uptime monitoring. Free tier with 5 monitors.
- **datadoghq.com** - Free for up to 5 nodes.
- **deadmanssnitch.com** - Monitoring for cron jobs. One free snitch.
- **Grafana Cloud** - Composable observability platform. Free: 3 users, 10 dashboards, 100 alerts.
- **healthchecks.io** - Monitor your cron jobs and background tasks. Free for up to 20 checks.
- **instatus.com** - Beautiful status page in 10 seconds. Free forever.
- **netdata.cloud** - Open-source tool to collect real-time metrics.
- **newrelic.com** - Observability platform. Free tier: 100GB/month data ingest, 1 full-access user.
- **statuscake.com** - Website monitoring, unlimited tests free with limitations.
- **UptimeRobot** - Free uptime monitoring. 50 monitors with 5-minute check intervals.

[⬆️ Back to Top](#table-of-contents)

## Crash and Exception Handling

- **Axiom** - Store up to 0.5 TB of logs with 30-day retention.
- **Bugsink** - Error-tracking with Sentry-SDK compatibility. Free up to 5,000 errors/month.
- **bugsnag.com** - Free for up to 2,000 errors/month after the initial trial.
- **elmah.io** - Error logging and uptime monitoring. Free Small Business subscription for open-source.
- **exceptionless** - Real-time error, feature, log reporting. Free for 3k events/month, 1 user.
- **GlitchTip** - Simple, open-source error tracking. 1000 events/month free.
- **honeybadger.io** - Exception, uptime, and cron monitoring. Free for small teams (12,000 errors/month).
- **rollbar.com** - Exception and error monitoring. Free plan with 5,000 errors/month.
- **sentry.io** - Tracks app exceptions in real-time. Free for 5k errors/month.

[⬆️ Back to Top](#table-of-contents)

## Search

- **algolia.com** - Hosted search solution. Free "Build" plan: 1M documents and 10K searches/month.
- **bonsai.io** - Free 1 GB memory and 1 GB storage.
- **CommandBar** - Unified Search Bar as-a-service. Free for up to 1,000 Monthly Active Users.
- **searchly.com** - Free 2 indices and 20 MB storage.

[⬆️ Back to Top](#table-of-contents)

## Education and Career Development

- **Cisco Networking Academy** - Free certification-aligned courses (cybersecurity, networking, Python).
- **DeepLearning.AI Short Courses** - Free short courses on generative AI tools and techniques.
- **edX** - Over 4,000 free online courses from 250 leading institutions.
- **Exercism** - Free, open-source programming education in 75+ languages with human mentoring.
- **FreeCodeCamp** - Free courses and certifications in Data Analysis, Web Development, and more.
- **Full Stack Open** - Free university-level course on modern web development.
- **Khan Academy** - Free online guides for HTML/CSS, JavaScript and SQL.
- **MIT OpenCourseWare** - Materials from over 2,500 MIT courses, freely shared.
- **Roadmap.sh** - Free learning roadmaps covering all aspects of development.
- **The Odin Project** - Free, open-source platform focused on JavaScript and Ruby.
- **W3Schools** - Free tutorials on web development technologies.

[⬆️ Back to Top](#table-of-contents)

## Email

- **10minutemail** - Free, temporary email for testing.
- **AhaSend** - Transactional email service. Free for 1000 emails/month.
- **AnonAddy** - Open-source anonymous email forwarding. Unlimited email aliases free.
- **Brevo** - 9,000 emails/month, 300 emails/day free.
- **Buttondown** - Newsletter service. Up to 100 subscribers free.
- **EmailJS** - Email client to send emails from the client. Free: 200 monthly requests, 2 templates.
- **EmailOctopus** - Up to 2,500 subscribers and 10,000 emails per month free.
- **forwardemail.net** - Free email forwarding for custom domains.
- **ImprovMX** - Free email forwarding.
- **MailerLite.com** - 1,000 subscribers/month, 12,000 emails/month free.
- **MailerSend.com** - Email API, SMTP, 3,000 emails/month free for transactional.
- **mailinator.com** - Free, public email system.
- **Mailjet** - 6,000 emails/month free (200 emails daily sending limit).
- **Mailtrap.io** - Email API, SMTP, 3,500 emails/month free. Email Sandbox for development.
- **Postmark** - 100 emails/month free, unlimited DMARC weekly digests.
- **Proton Mail** - Free secure email with end-to-end encryption. Free 1GB storage.
- **Resend** - Transactional emails API. 3,000 emails/month, 100 emails/day free.
- **Sender** - Up to 15,000 emails/month, up to 2,500 subscribers.
- **SimpleLogin** - Open source email alias/forwarding. Free 10 Aliases, unlimited reply/send.
- **Substack** - Unlimited free newsletter service.
- **temp-mail.io** - Free disposable temporary email service.
- **trashmail.com** - Free disposable email addresses with forwarding.
- **Tuta** - Free secure email with end-to-end encryption. Free 1GB storage.
- **Verifalia** - Real-time email verification API. 25 free verifications/day.

[⬆️ Back to Top](#table-of-contents)

## Feature Toggles Management Platforms

- **Abby** - Open-Source feature flags & A/B testing. Generous free tier.
- **ConfigCat** - Feature flag service. Free plan: up to 10 flags, 2 environments, 5 Million requests/month.
- **Flagsmith** - Manage feature flags across web, mobile, and server-side applications.
- **GrowthBook** - Open source feature flag and A/B testing. Free for up to 3 users.
- **Rollgate** - Feature flag management. Free plan: up to 500K API requests/month, unlimited flags.
- **Hypertune** - Type-safe feature flags, A/B testing, analytics. Free for up to 5 team members.
- **Statsig** - Feature management, A/B testing, analytics. Free up to 1 million events/month.
- **Toggled.dev** - Scalable feature toggles management. Free plan: up to 10 flags, 2 environments.

[⬆️ Back to Top](#table-of-contents)

## Font

- **Befonts** - Provides several unique fonts for personal or commercial use.
- **Bunny** - Privacy oriented Google Fonts.
- **dafont** - Fonts that are freeware, shareware, demo versions, or public domain.
- **Everything Fonts** - Offers multiple tools: @font-face, Units Converter, Font Hinter, Font Submitter.
- **Font Squirrel** - Freeware fonts licensed for commercial work.
- **Fontshare** - Free fonts service. 100% free for personal and commercial use.
- **Google Fonts** - Many free fonts easy to install via download or link to Google's CDN.

[⬆️ Back to Top](#table-of-contents)

## Forms

- **FabForm** - Form backend platform. Free plan: 250 form submissions/month.
- **Feathery** - Developer-friendly form builder. Free plan: up to 250 submissions/month, 5 active forms.
- **feedback.fish** - Free plan allows collecting 25 total feedback submissions.
- **Form.taxi** - Endpoint for HTML forms submissions. Free plan for basic usage.
- **Formcarry.com** - HTTP POST Form endpoint. Free plan: 100 monthly submissions.
- **Forminit** - Headless form backend. Free plan: 100 form submissions/month.
- **FormKeep.com** - Unlimited forms with 50 monthly submissions.
- **formspark.io** - Form to Email service. Free plan: unlimited forms, 250 submissions/month.
- **Formspree.io** - Send email using an HTTP POST request. Free: 50 submissions per form/month.
- **Formsubmit.co** - Easy form endpoints for your HTML forms. Free Forever.
- **HeroTofu.com** - Forms backend with bot detection. Free plan: unlimited forms, 100 submissions/month.
- **HeyForm.net** - Drag and drop online form builder. Free tier: unlimited forms and submissions.
- **Jotform.com** - Create online forms free. Free plan: 5 forms, 100 monthly submissions.
- **Kwes.io** - Feature rich form endpoint. Free plan: 1 website, up to 50 monthly submissions.
- **Pageclip** - Free plan: 1 site, 1 form, 1,000 monthly submissions.
- **smartforms.dev** - Form backend. Free plan: 50 submissions/month, 250MB file storage.
- **staticforms.xyz** - Integrate HTML forms without server-side code for free.
- **Tally.so** - 99% of all features free. Unlimited forms and submissions.
- **Typeform.com** - Beautifully designed forms. Free plan: 10 fields per form, 100 monthly responses.
- **Web3Forms** - Contact forms for Static & JAMStack Websites. Free: Unlimited Forms, 250 Submissions/month.
- **Wufoo** - Quick forms to use on websites. Free plan: 100 submissions each month.

[⬆️ Back to Top](#table-of-contents)

## Generative AI

- **Arize AX** - AI engineering platform to evaluate and observe AI applications. Free: 25k spans, 1gb/month.
- **Braintrust** - Evals, prompt playground, and data management for Gen AI. Free: up to 1,000 private eval rows/week.
- **Comet Opik** - Evaluate, test, and ship LLM applications. Open source.
- **Future AGI** - Open-source platform to evaluate, observe, and improve LLM and AI agent apps. Free tier: 50GB storage, 2K eval credits.
- **Keywords AI** - LLM monitoring platform. 10,000 free requests every month.
- **Langfuse** - Open-source LLM engineering platform. Free forever: 50k observations/month.
- **Langtrace** - Trace, evaluate, manage prompts and datasets. Free plan: 50K traces/month.
- **LangWatch** - LLMOps platform. Free plan: 1k traces/month.
- **Maxim** - LLM evaluation and observability platform. Free tier: 10k monthly logs.
- **OpenRouter** - Various free AI models (DeepSeek R1, V3, Llama, Moonshot AI), subject to rate limits.
- **Pollinations.AI** - Easy-to-use, free image generation AI with free API. No signups required. Open source.
- **Portkey** - Control panel for Gen AI apps. Free: up to 10,000 requests/month.
- **ReportGPT** - AI Powered Writing Assistant. Free as long as you bring your own API key.

[⬆️ Back to Top](#table-of-contents)

## IaaS

- **4EVERLAND** - Compatible with AWS S3 APIs. Free: 6 GB IPFS storage, 300MB Arweave storage.
- **backblaze.com** - Backblaze B2 cloud storage. Free 10 GB object storage for unlimited time.
- **filebase.com** - S3 Compatible Object Storage Powered by Blockchain. 5 GB free storage.
- **Modal** - AI-driven IaaS with compute, storage; offers free monthly credits.

[⬆️ Back to Top](#table-of-contents)

## Managed Data Services

- **8base.com** - Full-stack low-code development platform on MySQL and GraphQL. Free: 2,500 rows, 500 storage.
- **airtable.com** - Relational database. Unlimited bases, 1,200 rows/base, 1,000 API requests/month.
- **Aiven** - Free PostgreSQL, MySQL and Valkey plans. Single node, 1 CPU, 1GB RAM.
- **CockroachDB Cloud** - Free tier: 50 million RUs and 10 GiB of storage per month.
- **codehooks.io** - JavaScript serverless API/backend and NoSQL database. Free plan: 5GB storage.
- **Couchbase Capella** - Forever free fully managed database cluster: 1 node, 8GB storage.
- **CrateDB** - Distributed Open Source SQL database. Free Tier: 1 node, 2 CPUs, 2 GiB memory, 8 GiB storage.
- **filess.io** - Create 2 databases (MySQL, MariaDB, MongoDB, PostgreSQL), up to 10 MB each, free.
- **InfluxDB** - Timeseries database, free with reasonable limits.
- **MemCachier** - Managed Memcache service. Free for up to 25MB, 1 Proxy Server.
- **MongoDB Atlas** - Free tier gives 512 MB.
- **Neo4j Aura** - Managed native Graph DBMS. Limits: 200k nodes, 400k relationships.
- **Neon** - Managed PostgreSQL. 0.5 GB storage per project, 100 Projects, unlimited databases.
- **Nile** - A Postgres platform for B2B apps. Unlimited databases, 1GB storage.
- **Prisma Postgres** - Hosted Postgres. 500MB total storage, 5 databases, integrated with Prisma ORM.
- **Qdrant** - Vector Database. Single node cluster with 0.5 vCPU, 1GB RAM, 4GB disk.
- **restdb.io** - NoSQL cloud database. Free plan: 3 users, 2500 records, 1 API request/second.
- **SeaTable** - Spreadsheet-like Database. Unlimited tables, 2,000 lines, up to 25 team members.
- **Tinybird** - Serverless managed ClickHouse. Free: 10GB storage + 1000 API requests/day.
- **Turso** - SQLite Edge Database. Free Forever: 9 GB storage, up to 500 databases, 1 billion row reads/month.
- **Upstash** - Serverless Redis. Free: up to 500K monthly commands, 256MB max database size.

[⬆️ Back to Top](#table-of-contents)

## Tunneling, WebRTC, Web Socket Servers and Other Routers

- **btunnel** - Expose localhost to the internet. Free: file server, basic auth, 1 hour tunnel timeout.
- **cname.dev** - Free and secure dynamic reverse proxy service.
- **conveyor.cloud** - Visual Studio extension to expose IIS Express over a tunnel to a public URL.
- **Expose** - Expose local sites via secure tunnels. Free plan: EU Server, random subdomains.
- **Hamachi** - Hosted VPN service. Free plan allows unlimited networks with up to 5 people.
- **Hookdeck** - Develop, test, and monitor webhooks. 100K requests/month with 3 days retention.
- **localhost.run** - Expose locally running servers over a tunnel to a public URL.
- **localtunnel** - Expose locally running servers over a tunnel. Free hosted version, and open source.
- **LocalXpose** - Reverse proxy to expose localhost. Free plan: 15 minutes tunnel lifetime.
- **ngrok.com** - Expose locally running servers over a tunnel to a public URL.
- **Pinggy** - Public URLs for localhost. Free plan: 60 minutes tunnel lifetime.
- **serveo** - Expose local servers to the internet. No installation, no signup.
- **Tailscale** - Zero config VPN using WireGuard. Free plan for personal use: 100 devices, 3 users.
- **webhookrelay.com** - Manage, debug, fan-out, and proxy webhooks.
- **Xirsys** - Unlimited STUN usage + 500 MB monthly TURN bandwidth.
- **ZeroTier** - FOSS managed virtual Ethernet. Unlimited networks of 25 clients on the free plan.

[⬆️ Back to Top](#table-of-contents)

## Issue Tracking and Project Management

- **asana.com** - Free for private project with collaborators.
- **Backlog** - Free plan: 1 Project with 10 users & 100MB storage.
- **Basecamp** - To-do lists, messaging, file sharing, time tracking. Up to 3 projects, 20 users, 1GB.
- **bitrix24.com** - Intranet and project management. Free plan: 5GB for unlimited users.
- **clickup.com** - Project management. Free with cloud storage and Git integrations.
- **Clockify** - Time tracker and timesheet app. Unlimited users, free forever.
- **Confluence** - Content collaboration tool. Free plan for up to 10 users.
- **diagrams.net** - Online diagrams stored locally. Free for all features.
- **freedcamp.com** - Tasks, discussions, milestones, time tracking. Free plan: unlimited projects, users, storage.
- **Jira** - Software development project management. Free plan for up to 10 users.
- **kanbanflow.com** - Board-based project management. Free, premium version with more options.
- **Linear** - Issue tracker. Free for unlimited members, up to 250 issues.
- **Lucidchart** - Online diagram tool. Free plan: 3 editable documents, 100 templates.
- **MeisterTask** - Online task management. Free up to 3 projects, unlimited members.
- **nTask** - Project management. Essential plan free forever: 100 MB storage, 5 users/teams.
- **Plane** - Open-source project and product management. Free for unlimited members, up to 1000 issues.
- **Shortcut** - Project management platform. Free for up to 10 users forever.
- **taiga.io** - Project management for startups and agile developers, free for Open Source.
- **taskade.com** - Real-time collaborative task lists. Free plan: 1 workspace, unlimited tasks.
- **todoist.com** - Task management. Free plan: 5 active projects, 5 users per project.
- **trello.com** - Board-based project management. Unlimited Personal Boards, 10 Team Boards.
- **YouTrack** - Free hosted YouTrack for FOSS and private projects (free for 3 users).
- **zenhub.com** - Project management inside GitHub. Free for public repos, OSS, and nonprofits.

[⬆️ Back to Top](#table-of-contents)

## Storage and Media Processing

- **AndroidFileHost** - Free file-sharing platform with unlimited speed and bandwidth.
- **borgbase.com** - Offsite backup hosting for Borg Backup. 10 GB free backup space and 2 repositories.
- **cloudinary.com** - Image upload, manipulations, storage, and delivery. Free tier: 25 monthly credits.
- **degoo.com** - AI based cloud storage with free up to 20 GB, 3 devices.
- **Ente** - End-to-end encrypted cloud for photos, videos and 2FA secrets. Free 10GB.
- **file.io** - 2 GB storage of files. File auto-deleted after one download.
- **GoFile.io** - Free file sharing and storage. Unlimited file size and bandwidth.
- **icedrive.net** - Simple cloud storage service. 10 GB free storage.
- **imagekit.io** - Image CDN with optimization and transformation. Free: up to 20GB bandwidth/month.
- **ImgBB** - Unlimited image hosting service. 32 MB/image limit.
- **Imgbot** - Optimizes your images. Free for open source.
- **imgix** - Image Caching, management and CDN. Free: 1000 origin images, 100 GB bandwidth.
- **internxt.com** - Zero-knowledge file storage. 10 GB for free, forever.
- **kraken.io** - Image optimization. Free plan: up to 1 MB file size.
- **pcloud.com** - Cloud storage service. Up to 10 GB of free storage.
- **Pinata IPFS** - Upload and manage files on IPFS. 1 GB storage free, plus API access.
- **Proton Drive** - Ultra-secure cloud storage. Free plan: 5gb of storage.
- **resmush.it** - FREE API providing image optimization.
- **sirv.com** - Smart Image CDN. Free tier: 500 MB storage and 2 GB bandwidth.
- **sync.com** - End-to-End cloud storage service. 5 GB free storage.
- **tinypng.com** - API to compress and resize PNG and JPEG images. 500 compressions free each month.
- **transloadit.com** - Handles file uploads and encoding. Free for Open source, charities, and students.
- **twicpics.com** - Responsive images as a service. Free for up to 3GB of traffic/month.
- **uploadcare.com** - Media pipeline toolkit. Free tier: 3000 uploads, 3 GB traffic, 3 GB storage.

[⬆️ Back to Top](#table-of-contents)

## Design and UI

- **BoxySVG** - A free Web app for drawing SVGs and exporting in multiple formats.
- **Canva** - Free online design tool to create visual content.
- **Excalidraw** - A free online drawing document web page.
- **figma.com** - Online, collaborative design tool. Free tier: unlimited files, 2 editors, 3 projects.
- **landen.co** - Generate, edit, and publish websites and landing pages. Free tier: one website.
- **marvelapp.com** - Design, prototyping, and collaboration. Free plan: 1 user and project.
- **Mockplus iDoc** - Design collaboration & handoff tool. Free Plan: 3 users and 5 projects.
- **photopea.com** - Advanced online design editor with Adobe Photoshop UI.
- **Plasmic** - Web design tool and page builder that integrates into your codebase.
- **Quant Ux** - Prototyping and design tool. Completely free and open source.
- **smartmockups.com** - Create product mockups. 200 free mockups.
- **TeleportHQ** - Low-code Front-end Design & Development Platform. 3 free projects, free code export.
- **Unicorn Platform** - Effortless landing page builder with hosting. One website for free.
- **Webflow** - WYSIWYG website builder with animations and hosting. Free for 2 projects.
- **Webstudio** - Open-source alternative to Webflow. Free: unlimited websites on their domain.
- **whimsical.com** - Collaborative flowcharts, wireframes, sticky notes and mind maps. Up to 4 free boards.
- **Zeplin** - Designer and developer collaboration platform. Free for one project.

[⬆️ Back to Top](#table-of-contents)

## Data Visualization on Maps

- **Clockwork Micro** - Map tools. 50,000 free monthly queries.
- **Foursquare** - Location discovery, venue search from Places API and Pilgrim SDK.
- **geoapify.com** - Vector and raster map tiles, geocoding, routing, isolines APIs. 3,000 free requests/day.
- **geocod.io** - Geocoding via API or CSV Upload. 2,500 free queries/day.
- **graphhopper.com** - Free developer package for Routing, Distance Matrix, Geocoding, Map Matching.
- **here** - APIs and SDKs for maps and location-aware apps. 250k transactions/month free.
- **locationiq.com** - Geocoding, Maps, and Routing APIs. 5,000 requests/day free.
- **mapbox.com** - Maps, geospatial services and SDKs.
- **maptiler.com** - Vector maps and SDKs. Free vector tiles with weekly updates.
- **nominatim.org** - OpenStreetMap's free geocoding service.
- **opencagedata.com** - Geocoding API aggregating OpenStreetMap. 2,500 free queries/day.
- **positionstack** - Free geocoding for global places. 25,000 Requests/month for personal use.
- **stadiamaps.com** - Map tiles, routing, navigation. 2,500 free map views and API requests/day.

[⬆️ Back to Top](#table-of-contents)

## Package Build System

- **build.opensuse.org** - Package build service for multiple distros (SUSE, EL, Fedora, Debian, etc.).
- **copr.fedorainfracloud.org** - Mock-based RPM build service for Fedora and EL.
- **help.launchpad.net** - Ubuntu and Debian build service.

[⬆️ Back to Top](#table-of-contents)

## IDE and Code Editing

- **Android Studio** - Open Source IDE for Android app development. Windows, Mac, Linux, ChromeOS.
- **AndroidIDE** - An Open Source IDE to develop Gradle-based Android applications on Android devices.
- **Apache NetBeans** - Development Environment, Tooling Platform and Application Framework.
- **BBEdit** - Extensible editor for macOS. Free Mode provides a powerful core feature set.
- **BlueJ** - A free Java Development Environment designed for beginners.
- **Brackets** - Open-source text editor designed for web development.
- **cacher.io** - Code snippet organizer with labels and support for 100+ languages.
- **cocalc.com** - Collaborative calculation in the cloud. Browser access to full Ubuntu.
- **Code::Blocks** - Free Fortran & C/C++ IDE. Open Source on Windows, macOS, Linux.
- **codiga.io** - Coding Assistant for code snippets. Free for individuals and small organizations.
- **Eclipse Che** - Web-based and Kubernetes-Native IDE. Open Source.
- **GetVM** - Instant free Linux and IDEs chrome sidebar. Free tier: 5 VMs per day.
- **JDoodle** - Online compiler and editor for 60+ languages. Free: 200 credits/day for REST API.
- **jetbrains.com** - IDEs (IntelliJ IDEA, PyCharm, etc). Free license for students, teachers, Open Source.
- **OneCompiler** - Free online compiler supporting 70+ languages.
- **OnlineGDB** - Free online IDE supporting 40+ languages with debugging.
- **Paiza** - Develop Web apps in Browser. Free Plan: 1 server, 24-hour lifetime, 4 hours/day running.
- **PHPSandbox** - Online development environment for PHP.
- **Replit** - A cloud coding environment for various languages.
- **SoloLearn** - A cloud programming playground. Free courses for beginners and intermediate coders.
- **stackblitz.com** - Online/Cloud Code IDE to create, edit & deploy full-stack apps.
- **Sublime Text** - Popular, versatile, customizable text editor.
- **Visual Studio Code** - Code editor optimized for building and debugging modern apps. By Microsoft.
- **Visual Studio Community** - Fully-featured IDE with thousands of extensions.
- **VSCodium** - Community-driven, telemetry-free, freely-licensed binary distribution of VSCode.
- **wakatime.com** - Quantified self-metrics about coding activity. Limited plan free.
- **Wave Terminal** - Open-source, cross-platform terminal. MacOS and Linux.

[⬆️ Back to Top](#table-of-contents)

## Analytics, Events and Statistics

- **amplitude.com** - 1 million monthly events, up to 2 apps.
- **Aptabase** - Open Source, Privacy-Friendly Analytics for Mobile and Desktop Apps. Free: up to 20,000 events/month.
- **Beampipe.io** - Privacy-focussed web analytics. Free for up to 5 domains & 10k monthly page views.
- **Clicky** - Website Analytics. Free Plan for 1 website with 3000 views analytics.
- **counter.dev** - Web analytics made simple and privacy friendly. Free or pay what you want.
- **getinsights.io** - Privacy-focused, cookie-free analytics. Free for up to 3k events/month.
- **GoatCounter** - Open-source web analytics. Free for non-commercial use: unlimited sites, 100k pageviews/month.
- **Google Analytics** - Google Analytics.
- **heap.io** - Automatically captures every user action. Free for up to 10K monthly sessions.
- **Microsoft Clarity** - Session recording completely free with no traffic limits.
- **Mixpanel** - 100,000 monthly tracked users, unlimited data history and seats.
- **PostHog** - Full Product Analytics suite free for up to 1m tracked events/month.
- **Rybbit** - Open-source, cookieless alternative to Google Analytics. Free: 3,000 monthly events.
- **Seline** - Simple & private website and product analytics. Free plan: 3,000 events/month.
- **StatCounter** - Website Viewer Analytics. Free plan for 500 most recent visitors.
- **Umami** - Simple, fast, privacy-focused, open-source alternative to Google Analytics.

[⬆️ Back to Top](#table-of-contents)

## Visitor Session Recording

- **FullStory.com** - 1,000 sessions/month with one month data retention and three user seats.
- **howuku.com** - Track user interaction and engagement. Free for up to 5,000 visits/month.
- **inspectlet.com** - 2,500 sessions/month free for one website.
- **LogRocket.com** - 1,000 sessions/month with 30-day retention, error tracking, live mode.
- **Microsoft Clarity** - Session recording completely free with no traffic or project limits.
- **mouseflow.com** - 500 sessions/month free for one website.
- **OpenReplay.com** - Open-source session replay. 1000 sessions/month, all features, 7-day retention.
- **smartlook.com** - Free packages for web and mobile apps (1500 sessions/month).
- **UXtweak.com** - Record how visitors use your website or app. Free unlimited time for small projects.

[⬆️ Back to Top](#table-of-contents)

## International Mobile Number Verification API and SDK

- **numverify** - Global phone number validation and lookup JSON API. 100 API requests/month.
- **veriphone** - Global phone number verification JSON API. 1000 requests/month.

[⬆️ Back to Top](#table-of-contents)

## Payment and Billing Integration

- **Adapty.io** - In-app subscription integration (iOS, Android, RN, Flutter, Unity, web). Free up to $10k monthly revenue.
- **Churnkey** - Cancel flows, churn metrics, and revenue analytics for subscriptions. Free forever.
- **CoinMarketCap** - Cryptocurrency market data. Free tier: 10K call credits/month.
- **Currencyapi** - Free currency conversion and exchange rate data API. Free: 300 requests/month.
- **CurrencyFreaks** - Current and historical currency exchange rates. Free: 1000 requests/month.
- **currencylayer** - Reliable Exchange Rates and Currency Conversion. 100 API requests/month free.
- **exchangerate-api.com** - Currency conversion JSON API. Free tier: 1,500 requests/month.
- **FraudLabsPRO** - Prevent payment fraud and chargebacks. Free Micro Plan: 500 queries/month.
- **Moesif API Monetization** - Generate revenue from APIs via usage-based billing. Free: 30,000 events/month.
- **ParityVend** - Adjust pricing based on visitor location (PPP). Free plan: 7,500 API requests/month.
- **Qonversion** - Cross-platform subscription management. Free up to $10k in monthly tracked revenue.
- **RevenueCat** - Hosted backend for in-app purchases and subscriptions. Free up to $2.5k/mo tracked revenue.
- **vatlayer** - Instant VAT number validation and EU VAT rates API. Free: 100 API requests/month.

[⬆️ Back to Top](#table-of-contents)

## Docker Related

- **Container Registry Service** - Harbor based Container Management. Free tier: 1 GB storage for private repositories.
- **Docker Hub** - One free private repository and unlimited public repositories.
- **Play with Docker** - A simple, interactive, fun playground to learn Docker.
- **quay.io** - Build and store container images with unlimited free public repositories.
- **ttl.sh** - Anonymous & ephemeral Docker image registry.

[⬆️ Back to Top](#table-of-contents)

## Dev Blogging Sites

- **AyeDot** - Share ideas in the form of modern multimedia short-format Miniblogs. Free.
- **BearBlog** - Minimalist, Markdown-powered blog and website builder.
- **Dev.to** - Where programmers share ideas and help each other grow.
- **Hashnode** - Hassle-free Blogging Software for Developers.
- **Medium** - Get more thoughtful about what matters to you.
- **JustBlogged** - Free blogging platform with custom domain support.

[⬆️ Back to Top](#table-of-contents)

## Screenshot APIs

- **ApiFlash** - A screenshot API based on AWS Lambda and Chrome.
- **microlink.io** - Turn any website into data or screenshots. 50 requests/day free.
- **PhantomJsCloud** - Browser automation and page rendering. Free: up to 500 pages/day.
- **screenshotbase.com** - 300 free screenshots/month from any url.
- **screenshotlayer.com** - Capture snapshots of any website. Free: 100 snapshots/month.
- **screenshotmachine.com** - Capture 100 snapshots/month, png, gif and jpg.
- **Screenshot Scout** - Clean screenshots from any URL. Free plan: 200 screenshots/month forever.
- **SnapAPI** - Screenshot, video, PDF, and web data extraction API. Free: 200 screenshots/month.
- **thumbnail.ws** - API for generating thumbnails of websites. Free: 1,000 requests/month.

[⬆️ Back to Top](#table-of-contents)

## Flutter Related and Building iOS Apps without Mac

- **CodeMagic** - Fully hosted CI/CD for mobile apps. Free tier: 500 free minutes/month, Mac Mini instance.
- **FlutLab** - Modern Flutter online IDE. Build iOS (without a Mac) and Android apps with Flutter.
- **FlutterFlow** - Browser-based drag-and-drop interface to build mobile apps using Flutter.

[⬆️ Back to Top](#table-of-contents)

## Privacy Management

- **Bearer** - Helps implement privacy by design via audits and workflows. Free tier for smaller teams.
- **Concord** - Full data privacy platform: consent management, DSARs, data mapping. Free tier with core features.
- **Cookiefirst** - Cookie banners, auditing, consent management. Free tier: one-time scan and single banner.
- **Iubenda** - Privacy and cookie policies and consent management. Free tier with limited features.
- **Ketch** - Consent management and privacy framework. Free tier with most features and limited visitor count.

[⬆️ Back to Top](#table-of-contents)

## PaaS

- **ampt.dev** - Build, deploy, and scale JavaScript apps on AWS. Free Preview plan: 50,000 invocations monthly.
- **anvil.works** - Web app development with nothing but Python. Free tier with unlimited apps.
- **appwrite** - Unlimited projects with authentication service. Free tier: 1 Database, 3 Buckets, 5 Functions per project.
- **Clever Cloud** - European PaaS with automated deployments. €20 free credits at signup, limited DEV plan.
- **Choreo** - AI-native internal developer platform. Free tier: up to 5 components and $100 credits/month.
- **Deno Deploy** - Runs JavaScript, TypeScript, WebAssembly at the edge. Free: 100,000 requests/day.
- **domcloud.co** - Linux hosting with CI/CD. Free version: 1 GB storage, 1 GB network/month.
- **encore.dev** - Backend framework with automatic infrastructure. Free cloud hosting for hobby projects.
- **gigalixir.com** - Free instance that never sleeps and free-tier PostgreSQL for Elixir/Phoenix apps.
- **Northflank** - Build and deploy microservices, jobs, databases. Free tier: 2 services, 2 cron jobs, 1 database.
- **pipedream.com** - Integration platform for developers. Workflows are code you can run for free.
- **pythonanywhere.com** - Cloud Python app hosting. Beginner account free: 1 Python web app, 512 MB storage.
- **WunderGraph** - Open-source platform to build modern APIs. Free plan: up to 3 projects, 1GB egress.
- **YepCode** - Connect APIs and services in a serverless environment. Free tier: 1,000 yeps.

[⬆️ Back to Top](#table-of-contents)

## Tools for Teams and Collaboration

- **3Cols** - A free cloud-based code snippet manager.
- **BookmarkOS.com** - Free all-in-one bookmark, tab, and task manager.
- **Calendly** - Connecting and scheduling meetings. Free plan: 1 Calendar connection per user.
- **Chanty.com** - Slack alternative. Free for small teams (up to 10), 20 GB storage per team.
- **Discord** - Chat with public/private rooms. Free for unlimited users.
- **Duckly** - Talk and collaborate in real time. Pair programming with IDE. Free for small teams.
- **element.io** - Decentralized and open-source communication tool built on Matrix.
- **evernote.com** - Tool for organizing information.
- **GitBook** - Platform for capturing and documenting technical knowledge. Free plan for individual developers.
- **gitter.im** - Chat, for GitHub. Unlimited public and private rooms, free for teams of up to 25.
- **Hackmd.io** - Real time collaboration & writing tool for markdown docs.
- **HeySpace** - Task management with chat, calendar, timeline and video calls. Free for up to 5 users.
- **Huly** - All-in-One Project Management Platform. Unlimited users, 10GB storage per workspace.
- **Keybase** - FOSS alternative to Slack; keeps chats and files safe.
- **Miro** - Collaboration whiteboard for distributed teams. Freemium plan.
- **Notion** - Note-taking and collaboration application with markdown support.
- **Nuclino** - Lightweight collaborative wiki. Free plan with all essential features, up to 50 items.
- **meet.jit.si** - One-click video conversations and screen sharing, for free.
- **Pumble** - Free team chat app. Unlimited users and message history, free forever.
- **Proton Pass** - Password manager with email aliases, 2FA, sharing and passkeys.
- **Raindrop.io** - Bookmarking app. Free Unlimited Bookmarks and Collaboration.
- **Revolt.chat** - OpenSource alternative to Discord that respects your privacy.
- **Rocket.Chat** - Open-source communication platform. Unlimited messaging.
- **Slab** - Modern knowledge management for teams. Free for up to 10 users.
- **slack.com** - Free for unlimited users with some feature limitations.
- **Telegram** - Fast, reliable messaging and calls. Large groups, file-sharing.
- **TimeCamp** - Free time tracking software for unlimited users.
- **tldraw.com** - Free open-source white-boarding and diagramming tool.
- **Webex** - Video meetings. Free plan: 40 minutes per meeting with 100 attendees.
- **whereby.com** - One-click video conversations, for free.
- **zoom.us** - Secure Video and Web conferencing. Free plan limited to 40 minutes.
- **Zulip** - Real-time chat with an email-like threading model. Free: 10,000 messages of search history.

[⬆️ Back to Top](#table-of-contents)

## DNS

- **1.1.1.1** - Free public DNS Resolver by Cloudflare, fast and secure.
- **1984.is** - Free DNS service with API and lots of other free DNS features.
- **cloudns.net** - Free DNS hosting up to 1 domain with 50 records.
- **deSEC** - Free DNS hosting with API support, designed with security in mind.
- **dns.he.net** - Free DNS hosting service with Dynamic DNS Support.
- **dnspod.com** - Free DNS hosting.
- **duckdns.org** - Free DDNS with up to 5 domains on the free tier.
- **Dynv6.com** - Free DDNS service with API support.
- **freedns.afraid.org** - Free DNS hosting plus free subdomains.
- **Glauca** - Free DNS hosting for up to 3 domains and DNSSEC support.
- **Hetzner** - Free DNS hosting with API support.
- **huaweicloud.com** - Free DNS hosting by Huawei.
- **LocalCert** - Free .localcert.net subdomains for use within private networks.
- **luadns.com** - Free DNS hosting, 3 domains, all features with reasonable limits.
- **namecheap.com** - Free DNS. No limit on the number of domains.
- **nextdns.io** - DNS-based firewall, 300K free queries monthly.
- **noip** - Dynamic DNS service. Up to 3 hostnames free with confirmation every 30 days.
- **sslip.io** - Free DNS service that returns an embedded IP address from a hostname.
- **zilore.com** - Free DNS hosting for 5 domains.
- **zoneedit.com** - Free DNS hosting with Dynamic DNS Support.
- **Zonomi** - Free DNS hosting with instant DNS propagation. Free plan: 1 DNS zone with up to 10 records.

[⬆️ Back to Top](#table-of-contents)

## Domain

- **DigitalPlat** - Free subdomains.
- **isroot.in** - Free isroot.in subdomains.
- **pp.ua** - Free pp.ua subdomains.

[⬆️ Back to Top](#table-of-contents)

## Web Hosting

- **Alwaysdata** - 1 GB free web hosting with broad language support. No custom domain on free plan.
- **Awardspace.com** - Free web hosting + free short domain, PHP, MySQL, App Installer.
- **boomurl** - Publish static sites to an instant HTTPS URL with no account.
- **Bubble** - Visual programming to build web and mobile apps without code, free with Bubble branding.
- **DigitalOcean** - Build and deploy 3 static sites free on the App Platform Starter tier.
- **FreeFlarum** - Community-powered free Flarum hosting for up to 250 users.
- **Kinsta Static Site Hosting** - Deploy up to 100 static sites free, custom domains with SSL, 100 GB bandwidth.
- **MDB GO** - Free hosting for 1 project, 500 MB RAM, 1G disk space.
- **Neocities** - Static, 1 GB free storage with 200 GB Bandwidth.
- **Netlify** - Builds, deploys and hosts static site/app free for 300 credits/month.
- **pantheon.io** - Drupal and WordPress hosting. Free for developers and agencies.
- **Qoddi** - PaaS similar to Heroku. Free tier for static assets, staging, and developer apps.
- **readthedocs.org** - Free documentation hosting with versioning, PDF generation.
- **render.com** - Unified cloud to build and run apps. Free plans for web services, databases, static pages.
- **surge.sh** - Static web publishing for Front-End developers. Unlimited sites with custom domain.
- **Vercel** - Build, deploy, and host web apps with free SSL and global CDN. Perfect for Next.js.
- **Versoly** - SaaS-focused website builder. Unlimited websites. No custom domain.

[⬆️ Back to Top](#table-of-contents)

## Commenting Platforms

- **GraphComment** - A comments platform to build an active community from the website's audience.
- **IntenseDebate** - A feature-rich comment system for WordPress, Tumblr, Blogger, and more.
- **Remarkbox** - Open source hosted comments platform, pay what you can.
- **Utterances** - A lightweight comments widget built on GitHub issues.

[⬆️ Back to Top](#table-of-contents)

## Remote Desktop Tools

- **AnyDesk** - Free for 3 devices, no limits on the number and duration of sessions.
- **Getscreen.me** - Free for 2 devices, no limits on the number and duration of sessions.
- **RemSupp** - On-demand support and permanent access to devices (2 sessions/day free).
- **RustDesk** - Open source virtual/remote desktop infrastructure for everyone.

[⬆️ Back to Top](#table-of-contents)

## Miscellaneous

- **Blynk** - SaaS with API to control, build & evaluate IoT devices. Free Developer Plan with 5 devices.
- **cron-job.org** - Online cronjobs service. Unlimited jobs free of charge.
- **Cronhooks** - Schedule one-time or recurring webhooks. Free plan: 5 ad-hoc schedules.
- **datelist.io** - Online booking / appointment scheduling. Free up to 5 bookings/month.
- **FOSSA** - Management for third-party code, license compliance and vulnerabilities.
- **Hook Relay** - Add webhook support to your app. Free plan: 100 deliveries/day, 14-day retention.
- **Hosting Checker** - Check hosting information for any domain, website or IP address.
- **newreleases.io** - Notifications on new releases from GitHub, GitLab, Bitbucket, PyPI, npm, and more.
- **PDFMonkey** - Manage PDF templates, call the API with dynamic data. 300 free documents/month.
- **QuickType.io** - Auto-generate models/types/serializers from JSON, schema, and GraphQL.
- **readme.com** - Beautiful documentation made easy, free for Open Source.
- **redirect.pizza** - Easily manage redirects with HTTPS support. Free plan: 10 sources, 100,000 hits/month.
- **ReqBin** - Post HTTP Requests Online. Supports Headers and Token Authentication.
- **Smartcar API** - An API for cars to locate, get fuel/battery levels, unlock/lock doors, etc.
- **Sunrise and Sunset** - Get sunrise and sunset times for a given longitude and latitude.
- **SurveyMonkey.com** - Create online surveys. Free plan: 10 questions and 100 responses per survey.
- **UUID Generator** - Generate UUID v1/v4/v7, GUID, Nil UUIDs, CUID, NanoID, and ULID instantly.

[⬆️ Back to Top](#table-of-contents)

## Other Free Resources

- **get.localhost.direct** - Wildcard public CA signed SSL cert for localhost development.
- **GitHub Education** - Collection of free services for students. Registration required.
- **Glob tester** - A website to design and test glob patterns.
- **Killer Coda** - Interactive playground to study Linux, Kubernetes, Containers, DevOps, Networking.
- **Microsoft 365 Developer Program** - Free sandbox, tools, and resources for the Microsoft 365 platform.
- **MySQL Visual Explain** - Free MySQL EXPLAIN output visualizer to optimize slow queries.
- **RedHat for Developers** - Free access to Red Hat products (RHEL, OpenShift, CodeReady, etc.) for developers.
- **SimpleBackups.com** - Backup automation for servers and databases. Free plan for 1 backup.
- **SnapShooter** - Backup solution for DigitalOcean, AWS, Hetzner, and more. Free plan with daily backups for one resource.

[⬆️ Back to Top](#table-of-contents)

---

*This list focuses on services with genuine free tiers (not just trials). Limits and offerings change over time — verify current terms on each provider's site before relying on them.*
