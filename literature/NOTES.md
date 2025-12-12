# Other Literature

There's an official list of papers using the dataset at: https://iab.de/dossier/?id=265000&q=unemployment&dokumententyp=Literaturhinweis&themenIds=266120,266121,266122,266123&beteiligte=&iab-beteiligte=&anzahl=100 (filtered by the keyword "unemployment" here).

We extracted all dois from this list with the following snippet.

```js
(function() {
    // 1. Select all list items which represent an entry
    const entries = document.querySelectorAll('li[class^="dossier-list-item-"]');
    
    // 2. Map over the selected entries to extract the data for each one
    const extractedData = Array.from(entries).map(entry => {
        
        // Helper function to safely get text content from an element or return null/undefined
        const getTextContent = (selector, parent = entry) => {
            const el = parent.querySelector(selector);
            // Use innerText to get rendered text, trim whitespace, and replace sequences of whitespace with a single space
            return el ? el.innerText.trim().replace(/\s+/g, ' ') : null;
        };

        // --- Basic Fields ---
        
        // Type (Dokumententyp)
        const type = getTextContent('#dossier-dokumententyp');

        // Title and Year
        let titleEl = entry.querySelector('#dossier-titel');
        let title = null;
        let year = null;
        if (titleEl) {
            // Title is within a <span>
            const titleSpan = titleEl.querySelector('span');
            title = titleSpan ? titleSpan.innerText.trim() : null;
            
            // Year is typically the text content outside the span, within parentheses
            const titleText = titleEl.textContent;
            const yearMatch = titleText.match(/\((\d{4})\)/);
            year = yearMatch ? yearMatch[1] : null;
        }

        // --- Authors ---
        
        const authorsContainer = entry.querySelector('#dossier-autoren');
        let authors = [];
        if (authorsContainer) {
            // Select all <span> elements that contain author names (excluding ORCID icon spans)
            // and filter out the ORCID link element if present.
            const authorSpans = Array.from(authorsContainer.querySelectorAll('span')).filter(span => {
                // Heuristic to exclude ORCID icon/screen-reader spans and similar utility spans
                return !span.classList.contains('orcid-icon') && !span.classList.contains('screen-reader-text');
            });
            
            authors = authorSpans.map(span => 
                // Clean up the name (remove trailing semicolon and trim)
                span.innerText.replace(/;$/, '').trim()
            ).filter(name => name.length > 0); // Filter out any empty strings
        }

        // --- Links ---
        
        // DOI/Primary Link (from dossier-bezugsmoeglichkeiten)
        let doiLink = null;
        const doiContainer = entry.querySelector('#dossier-bezugsmoeglichkeiten');
        if (doiContainer) {
            const linkEl = doiContainer.querySelector('a');
            doiLink = linkEl ? linkEl.href : null;
        }

        // --- Additional Information (inside show-additional div) ---
        const additionalInfoContainer = entry.querySelector('.show-additional');
        
        // Citation (Zitatform)
        const citation = getTextContent('#dossier-zitatform', additionalInfoContainer);
        
        // Abstract (Kurzbeschreibung)
        const abstract = getTextContent('#dossier-kurzbeschreibung', additionalInfoContainer);
        
        
        // --- Similar/Further Info Links (Ähnliche Treffer / Weiterführende Informationen) ---
        
        const otherLinks = [];
        // The structure uses repeated IDs ('dossier-treffer-1'), so we select by the container div class/id pattern
        const trefferDivs = additionalInfoContainer ? additionalInfoContainer.querySelectorAll('div[id^="dossier-treffer-"]') : [];
        
        Array.from(trefferDivs).forEach(div => {
            const linkEl = div.querySelector('a');
            if (linkEl) {
                // Get the link text and the URL
                const linkText = linkEl.textContent.trim().replace(/\s+/g, ' ');
                const linkUrl = linkEl.href;
                
                // Determine the category from the preceding h3
                let categoryEl = div.querySelector('h3');
                let category = categoryEl ? categoryEl.innerText.trim() : 'Weitere Information';

                otherLinks.push({
                    category: category,
                    text: linkText,
                    url: linkUrl
                });
            }
        });
        
        // 3. Return the consolidated object for the current entry
        return {
            type: type,
            title: title,
            year: year,
            authors: authors,
            doi_link: doiLink,
            citation: citation,
            abstract: abstract,
            other_links: otherLinks.length > 0 ? otherLinks : null
        };
    }).filter(item => item.title !== null); // Filter out any entries that couldn't extract a title

    // 4. Store the result in the global variable OUTPUT
    window.OUTPUT = extractedData;

    // 5. Output success message and variable content
    console.log(`✅ Successfully extracted ${extractedData.length} entries.`);
    console.log(`The data has been stored in the global variable \`OUTPUT\`.`);
    console.log('You can now access it by typing `OUTPUT` or copy it using `copy(JSON.stringify(OUTPUT, null, 2))`.');
    
    // Return the data for use in the console
    return extractedData;

})();

(function() {
    /**
     * Converts a flat or moderately nested JSON array into a CSV string.
     * Handles simple arrays (like 'authors') and nested arrays (like 'other_links') 
     * by summarizing the information into a single cell.
     * @param {Array<Object>} jsonArray - The array of JSON objects (your OUTPUT).
     * @param {string} delimiter - The delimiter to use (e.g., ',').
     * @returns {string} The CSV formatted string.
     */
    const convertToCSV = (jsonArray, delimiter = ',') => {
        if (!jsonArray || jsonArray.length === 0) {
            return '';
        }

        // --- 1. Define Column Headers (based on your structure) ---
        // We explicitly list the keys to control the order and add custom headers for nested data
        const headers = [
            'type', 
            'title', 
            'year', 
            'authors', 
            'doi_link', 
            'citation', 
            'abstract', 
            'other_links_summary' // Custom header for flattened link data
        ];
        
        // CSV header row
        let csv = headers.join(delimiter) + '\n';

        // --- 2. Process Data Rows ---
        
        jsonArray.forEach(item => {
            let row = [];
            
            headers.forEach(header => {
                let value = item[header];

                if (header === 'authors') {
                    // Handle the 'authors' array: join names with a semicolon or pipe
                    value = Array.isArray(value) ? value.join('; ') : '';
                } else if (header === 'other_links_summary') {
                    // Handle the 'other_links' array: serialize to a readable string
                    const links = item['other_links'];
                    if (Array.isArray(links)) {
                         // Format: "Category1: URL1 | Category2: URL2"
                         value = links.map(link => `${link.category}: ${link.url}`).join(' | ');
                    } else {
                        value = '';
                    }
                } else if (value === null || value === undefined) {
                    value = ''; // Ensure null/undefined values are empty strings
                }

                // Convert all values to strings and sanitize for CSV
                value = String(value).replace(/"/g, '""'); // Escape double quotes
                
                // If the value contains the delimiter, newlines, or double quotes, wrap it in double quotes
                if (value.includes(delimiter) || value.includes('\n') || value.includes('"')) {
                    value = `"${value}"`;
                }
                
                row.push(value);
            });
            
            csv += row.join(delimiter) + '\n';
        });

        return csv;
    };

    // --- Execution ---
    
    if (typeof window.OUTPUT === 'undefined' || window.OUTPUT.length === 0) {
        console.error('Error: Global variable OUTPUT is not defined or is empty. Please run the data extraction script first.');
        return;
    }

    const csvData = convertToCSV(window.OUTPUT);
    
    // Log the CSV data to the console
    console.log('--- Generated CSV Data (Copy from below) ---');
    console.log(csvData);
    console.log('-------------------------------------------');

    // Optional: Log a copy command for easy retrieval
    console.log('To copy the CSV to your clipboard, run:');
    console.log('copy(csvData)'); 
    
    // Store the CSV string in another global variable for easy access
    window.CSV_OUTPUT = csvData;
    
    return csvData;

})();
```

Copy into clipboard

```js
// Copy JSON output to clipboard on click
document.addEventListener('click', () => navigator.clipboard.writeText(JSON.stringify(OUTPUT, null, 2)).then(() => console.log('OUTPUT copied to clipboard!')).catch(err => console.error('Failed to copy OUTPUT:', err)), { once: true });

// Copy CSV output to clipboard on click
document.addEventListener('click', () => navigator.clipboard.writeText(CSV_OUTPUT).then(() => console.log('CSV_OUTPUT copied to clipboard!')).catch(err => console.error('Failed to copy CSV_OUTPUT:', err)), { once: true });
```
