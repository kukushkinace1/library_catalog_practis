# Manual CRUD Check

Base URL:

```powershell
$baseUrl = "http://127.0.0.1:8000/api/v1"
```

## 1. Health check

```powershell
Invoke-RestMethod `
    -Method GET `
    -Uri "$baseUrl/health/" | ConvertTo-Json -Depth 10
```

Expected:
- `status` is `healthy`
- `database` is `connected`

## 2. Create book

```powershell
$createBody = @{
    title = "Clean Code"
    author = "Robert Martin"
    year = 2008
    genre = "Programming"
    pages = 464
    isbn = "9780132350884"
    description = "A handbook of agile software craftsmanship"
} | ConvertTo-Json

$created = Invoke-RestMethod `
    -Method POST `
    -Uri "$baseUrl/books/" `
    -ContentType "application/json" `
    -Body $createBody

$created | ConvertTo-Json -Depth 10
```

Expected:
- book is created
- response contains `book_id`
- `extra` is filled if Open Library enrichment succeeds

Save ID for next steps:

```powershell
$bookId = $created.book_id
$bookId
```

## 3. Get book by ID

```powershell
Invoke-RestMethod `
    -Method GET `
    -Uri "$baseUrl/books/$bookId" | ConvertTo-Json -Depth 10
```

Expected:
- the same book is returned
- `book_id` matches `$bookId`

## 4. Get books list

```powershell
Invoke-RestMethod `
    -Method GET `
    -Uri "$baseUrl/books/?page=1&page_size=10" | ConvertTo-Json -Depth 10
```

Expected:
- response contains items list
- created book is present in the list

## 5. Filter books

```powershell
Invoke-RestMethod `
    -Method GET `
    -Uri "$baseUrl/books/?title=Clean&author=Robert&page=1&page_size=10" | ConvertTo-Json -Depth 10
```

Expected:
- response contains the created book
- filters work correctly

## 6. Update book

```powershell
$updateBody = @{
    pages = 500
    description = "Updated description"
    available = $false
} | ConvertTo-Json

Invoke-RestMethod `
    -Method PATCH `
    -Uri "$baseUrl/books/$bookId" `
    -ContentType "application/json" `
    -Body $updateBody | ConvertTo-Json -Depth 10
```

Expected:
- `pages` becomes `500`
- `description` is updated
- `available` becomes `false`

## 7. Delete book

```powershell
Invoke-WebRequest `
    -Method DELETE `
    -Uri "$baseUrl/books/$bookId"
```

Expected:
- status code is `204`

## 8. Verify delete

```powershell
Invoke-RestMethod `
    -Method GET `
    -Uri "$baseUrl/books/$bookId"
```

Expected:
- API returns `404`

## 9. Negative test: duplicate ISBN

```powershell
$duplicateBody = @{
    title = "Clean Code"
    author = "Robert Martin"
    year = 2008
    genre = "Programming"
    pages = 464
    isbn = "9780132350884"
    description = "Duplicate ISBN test"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method POST `
    -Uri "$baseUrl/books/" `
    -ContentType "application/json" `
    -Body $duplicateBody
```

Expected:
- first request may succeed
- repeated request should return `409`

## 10. Negative test: invalid pages

```powershell
$invalidBody = @{
    title = "Bad Book"
    author = "Test Author"
    year = 2020
    genre = "Test"
    pages = 0
    isbn = "1234567890"
    description = "Invalid pages test"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method POST `
    -Uri "$baseUrl/books/" `
    -ContentType "application/json" `
    -Body $invalidBody
```

Expected:
- API returns `400`

## 11. Negative test: not found

```powershell
Invoke-RestMethod `
    -Method GET `
    -Uri "$baseUrl/books/11111111-1111-1111-1111-111111111111"
```

Expected:
- API returns `404`

## Outputs

Paste command outputs below this line.
