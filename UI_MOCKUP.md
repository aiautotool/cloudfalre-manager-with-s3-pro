# Cloud Management Pro - UI Mockup

## Application Overview
**Title**: Cloud Management Pro  
**Window Size**: 1000×800 pixels  
**Theme**: Dark Mode  
**Framework**: CustomTkinter  

---

## Tab 1: Cloudflare DNS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Cloud Management Pro                                                   ⚫ ⚫ │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Cloudflare DNS] [AWS S3]                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  Cloudflare Settings                                                  ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                       ║ │
│  ║  API Token:  [●●●●●●●●●●●●●●●●●●●●●●●●●●]  [Load Domains]           ║ │
│  ║                                                                       ║ │
│  ║  Select Domain:  [example.com              ▼]  [Save CF Config]      ║ │
│  ║                                                                       ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  Add New Record                                                       ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                       ║ │
│  ║  Subdomain: [www      ] Type: [A  ▼] Content: [192.168.1.1        ]  ║ │
│  ║                                                                       ║ │
│  ║  TTL: [Auto ▼]  ☑ Proxied  [Create Record] [Clear]                   ║ │
│  ║                                                                       ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║  [Refresh Records] [Delete Selected] [Export MikroTik]               ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║  Type │ Name                  │ Content / IP    │ Record ID         ║ │
│  ╟───────┼───────────────────────┼─────────────────┼───────────────────╢ │
│  ║  A    │ www.example.com       │ 192.168.1.1     │ abc123...         ║ │
│  ║  CNAME│ blog.example.com      │ www.example.com │ def456...         ║ │
│  ║  A    │ api.example.com       │ 10.0.0.5        │ ghi789...         ║ │
│  ║  CNAME│ cdn.example.com       │ cdn.cloudflare  │ jkl012...         ║ │
│  ║       │                       │                 │                   ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Ready                                                    [████████░░] 80%  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Color Scheme - Cloudflare DNS Tab
- **Background**: `#2b2b2b` (Dark gray)
- **Panels**: `#333333` (Medium dark)
- **Primary Button**: `#3498db` (Blue) → Hover: `#2980b9`
- **Success Button**: `#27ae60` (Green) → Hover: `#006400`
- **Danger Button**: `#C0392B` (Red) → Hover: `#962D22`
- **Text**: `#ffffff` (White)
- **Selection**: `#3498db` (Blue)

---

## Tab 2: AWS S3

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Cloud Management Pro                                                   ⚫ ⚫ │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Cloudflare DNS] [AWS S3]                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔══════════════════════╗  ╔═════════════════════════════════════════════╗ │
│  ║ AWS Profiles & Config║  ║ Current Bucket Management                   ║ │
│  ╠══════════════════════╣  ╠═════════════════════════════════════════════╣ │
│  ║                      ║  ║                                             ║ │
│  ║ Profile: [Default ▼] ║  ║ Bucket Name: [my-website-bucket           ] ║ │
│  ║          [Save][Del] ║  ║              [+ New Bucket]                 ║ │
│  ║                      ║  ║                                             ║ │
│  ║ Access: [AKIA...   ] ║  ║ ☑ Hosting  Idx:[index.html] Err:[404.html] ║ │
│  ║ Secret: [●●●●●●●●●●] ║  ║                                             ║ │
│  ║ Region: [us-east-1 ] ║  ║ [Apply Web & Policy] [Delete Bucket]        ║ │
│  ║                      ║  ║                                             ║ │
│  ║ [Load S3 Buckets]    ║  ║ URL: [http://my-website.s3-website...] [📋] ║ │
│  ║                      ║  ║                                             ║ │
│  ║ [Search buckets...  ]║  ║ ☑ Link Cloudflare DNS                       ║ │
│  ║                      ║  ║ Sub:[static    ] ☑Proxy  [⚡ Add DNS]       ║ │
│  ║ ┌──────────────────┐ ║  ║                                             ║ │
│  ║ │my-website-bucket │ ║  ╠═════════════════════════════════════════════╣ │
│  ║ │static-assets-prod│ ║  ║ [Objects][Permissions][PAB][Hosting][CORS]  ║ │
│  ║ │data-backup-2024  │ ║  ╟─────────────────────────────────────────────╢ │
│  ║ │images-cdn        │ ║  ║ [Upload File][Upload Folder][Download][Del] ║ │
│  ║ │logs-archive      │ ║  ║ Search: [Filter objects...        ][Refresh]║ │
│  ║ │                  │ ║  ╟─────────────────────────────────────────────╢ │
│  ║ │                  │ ║  ║ Name/Key │ Last Modified │ Size │ Class     ║ │
│  ║ │                  │ ║  ╟──────────┼───────────────┼──────┼───────────╢ │
│  ║ └──────────────────┘ ║  ║ index.ht │ 2024-12-27    │ 5.2K │ STANDARD  ║ │
│  ║                      ║  ║ style.css│ 2024-12-27    │ 12K  │ STANDARD  ║ │
│  ║                      ║  ║ img/lo.. │ 2024-12-26    │ 45K  │ STANDARD  ║ │
│  ╚══════════════════════╝  ╚═════════════════════════════════════════════╝ │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Fetching details for my-website-bucket...              [████░░░░░░] 40%    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Layout - AWS S3 Tab
- **Left Sidebar**: 350px (fixed width)
  - AWS Configuration
  - Bucket List Table
  
- **Right Main Content**: Flexible width
  - Bucket Management Section
  - Tabbed Detail Views

### Color Scheme - AWS S3 Tab
- **Background**: Same as Cloudflare tab
- **Orange Accent**: `#E67E22` (Add DNS button) → Hover: `#D35400`
- **Success Green**: `#27ae60` 
- **Danger Red**: `#C0392B`
- **Info Blue**: `#3498db`

---

## UI Components Breakdown

### 1. Cloudflare DNS Tab Components

#### Configuration Section
| Component | Type | Properties |
|-----------|------|------------|
| API Token | Entry (Password) | Masked, width: 300px |
| Domain | ComboBox | Values from API |
| Load Domains | Button | Blue, width: 120px |
| Save CF Config | Button | Gray, width: 120px |

#### Add Record Section
| Component | Type | Properties |
|-----------|------|------------|
| Subdomain | Entry | Placeholder: "www" |
| Type | ComboBox | Values: A, AAAA, CNAME, TXT, MX, SRV, NS |
| Content | Entry | Placeholder: "1.2.3.4", width: 200px |
| TTL | ComboBox | Auto, 1min, 2min, 5min, etc. |
| Proxied | Checkbox | Default: unchecked |
| Create Record | Button | Green, hover: dark green |
| Clear | Button | Gray, width: 100px |

#### Records Table
| Column | Width | Content |
|--------|-------|---------|
| Type | 80px | DNS record type |
| Name | 250px | Full domain name |
| Content/IP | 200px | Target value |
| Record ID | Hidden | For backend reference |

### 2. AWS S3 Tab Components

#### Left Sidebar - AWS Config
| Component | Type | Properties |
|-----------|------|------------|
| Profile | ComboBox | Saved profiles |
| Save | Button | Green, width: 60px, height: 24px |
| Delete | Button | Red, width: 60px, height: 24px |
| Access Key | Entry | Visible text, height: 26px |
| Secret Key | Entry | Masked, height: 26px |
| Region | Entry | Default: "us-east-1", height: 26px |
| Load S3 Buckets | Button | Full width, height: 32px |

#### Left Sidebar - Bucket List
| Component | Type | Properties |
|-----------|------|------------|
| Search | Entry | Placeholder: "Search buckets..." |
| Bucket Table | Treeview | Single column: name |

#### Right Main - Bucket Management
| Component | Type | Properties |
|-----------|------|------------|
| Bucket Name | Entry | Width: 300px |
| New Bucket | Button | Blue, width: 100px |
| Hosting | Checkbox | Default: checked |
| Index Doc | Entry | Default: "index.html", width: 80px |
| Error Doc | Entry | Default: "404.html", width: 80px |
| Apply Web & Policy | Button | Green, width: 150px |
| Delete Bucket | Button | Red, width: 120px |
| Endpoint URL | Entry | Read-only |
| Copy | Button | Width: 60px |

#### Cloudflare Integration Section
| Component | Type | Properties |
|-----------|------|------------|
| Link Cloudflare DNS | Checkbox | Toggle integration |
| Subdomain | Entry | Width: 120px, placeholder: "e.g. static" |
| Proxy | Checkbox | Default: checked |
| ⚡ Add DNS | Button | Orange (#E67E22), width: 100px, **ALWAYS enabled when bucket selected** |

#### Detail Tabs
1. **Objects** - File management
2. **Permissions / Policy** - JSON policy viewer
3. **Public Access Block** - 4 settings display
4. **Website Hosting** - Configuration status
5. **CORS** - JSON CORS rules editor
6. **Versioning** - Enable/Suspend controls

---

## Status Bar (Both Tabs)

```
┌─────────────────────────────────────────────────────────┬───────────────────┐
│ Status message text here...                             │ [████████░░] 80%  │
└─────────────────────────────────────────────────────────┴───────────────────┘
```

- **Height**: 30px
- **Background**: `#1E1E1E`
- **Left**: Status text (white, 12px font)
- **Right**: Progress bar (200px width, 10px height)
  - Determinate mode: Shows percentage
  - Indeterminate mode: Animated when loading

---

## Typography

- **Headers**: SF Pro Display, 14-16px, Bold
- **Labels**: SF Pro Display, 12px, Regular
- **Buttons**: SF Pro Display, 12px, Medium
- **Table**: SF Pro Display, 11px (content), 12px (headers)
- **Status Bar**: SF Pro Display, 12px, Regular

---

## Interaction States

### Button States
- **Normal**: Base color
- **Hover**: Darker shade
- **Disabled**: Gray (#808080)
- **Pressed**: Even darker shade

### Entry States
- **Normal**: Dark background, white text
- **Focus**: Blue border (#3498db)
- **Disabled**: Gray background, gray text

### Table States
- **Normal Row**: Dark background
- **Hover Row**: Slightly lighter
- **Selected Row**: Blue background (#3498db)

---

## Key Features Highlighted in Mockup

### Cloudflare DNS
✅ Token-based authentication  
✅ Multiple domain support  
✅ Full DNS record CRUD  
✅ MikroTik export capability  
✅ Proxy toggle per record  
✅ TTL customization  

### AWS S3
✅ Multi-profile support  
✅ Bucket listing and search  
✅ Website hosting setup  
✅ File/folder upload  
✅ **NEW: Always-available DNS linking**  
✅ Auto-check for existing DNS  
✅ Smart endpoint detection  
✅ CORS configuration  
✅ Versioning control  
✅ Policy management  

---

## NEW DNS Feature Workflow

```
User Flow: Adding DNS for S3 Bucket
─────────────────────────────────────

1. Select Bucket
   └─> Button ⚡ Add DNS becomes ENABLED

2. (Optional) Adjust Subdomain
   └─> Auto-filled from bucket name

3. Click ⚡ Add DNS
   ├─> Status: "Checking DNS record..."
   ├─> Check if DNS exists
   │   ├─> EXISTS: Show info dialog, no change
   │   └─> NOT EXISTS: Create new DNS
   │       ├─> Use website endpoint (if available)
   │       └─> Use S3 bucket domain (if no website)
   └─> Status: "DNS created successfully" or "Already exists"

No requirement for website hosting!
```

---

## Responsive Behavior

- Window minimum size: 900×700px
- Tables expand to fill available space
- Sidebar fixed at 350px (S3 tab)
- Buttons maintain fixed widths
- Entries expand to fill parent width

---

## Accessibility Notes

- High contrast dark theme
- Clear visual hierarchy
- Distinct button colors for actions
- Loading states with progress indicators
- Error messages in red
- Success messages in green
- Disabled states clearly visible

---

*This mockup represents the current implementation of Cloud Management Pro with the enhanced DNS linking feature that allows flexible DNS record creation for S3 buckets.*
