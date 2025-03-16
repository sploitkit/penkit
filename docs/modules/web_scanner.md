# Web Vulnerability Scanner Module

The Web Vulnerability Scanner module scans web applications for vulnerabilities, focusing on SQL injection using SQLmap.

## Options

- `target_url`: Target URL to scan
- `data`: POST data to include with the request
- `cookie`: Cookies to use for the request
- `user_agent`: User agent to use for the request
- `scan_level`: Detection level (1-5)
- `risk_level`: Risk level (1-3)
- `forms`: Test forms on the page (true/false)
- `crawl_depth`: Crawl depth for discovering more URLs (0 = disabled)
- `threads`: Number of concurrent threads
- `timeout`: Scan timeout in seconds
- `scan_type`: Type of scan to perform (quick or thorough)

## Usage Examples

### Command Line

```bash
./run.sh
