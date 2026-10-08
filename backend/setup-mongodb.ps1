# Clarity MongoDB Atlas setup. Place this file inside backend, or pass -BackendPath.
[CmdletBinding()]
param(
    [string]$BackendPath = '',
    [ValidateRange(0, 600)]
    [int]$WaitSeconds = 180
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($BackendPath)) {
    if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $BackendPath = $PSScriptRoot
    } elseif (-not [string]::IsNullOrWhiteSpace($MyInvocation.MyCommand.Path)) {
        $BackendPath = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
    } else {
        $BackendPath = (Get-Location).Path
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $BackendPath 'app/config.py'))) {
    $nestedBackend = Join-Path $BackendPath 'backend'
    if (Test-Path -LiteralPath (Join-Path $nestedBackend 'app/config.py')) {
        $BackendPath = $nestedBackend
    } else {
        throw 'Cannot find backend/app/config.py. Place this script in backend or use -BackendPath.'
    }
}
$BackendPath = (Resolve-Path -LiteralPath $BackendPath).Path
$pythonPath = Join-Path $BackendPath '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Backend virtual environment is missing. Complete the Python dependency installation first.'
}
if (-not (Test-Path -LiteralPath (Join-Path $BackendPath '.env'))) {
    throw 'backend/.env is missing. Configure MONGODB_URI, MONGODB_DB_NAME and VECTOR_INDEX_NAME first.'
}

$mongoCode = @'
import asyncio
import sys
import time


async def setup(wait_seconds):
    from app.config import Settings
    from app.database.mongodb import MongoDatabase
    from pymongo.operations import SearchIndexModel

    settings = Settings()
    uri = settings.mongodb_uri.get_secret_value()
    if not uri or 'USERNAME:PASSWORD' in uri or 'YOUR_CLUSTER' in uri:
        print('ERROR: Replace the example MONGODB_URI in backend/.env.')
        return 1
    database = MongoDatabase(settings)
    try:
        print('1/3 Checking MongoDB connection...')
        await database.ping()
        print('Connected. Credentials are not printed.')

        print('2/3 Creating/verifying regular database indexes...')
        await database.ensure_indexes()
        print('Verified patients.email (unique), documents.patient_id, and medical_chunks ownership/type indexes.')

        print('3/3 Creating/verifying the Atlas vector index...')
        collection = database.db.medical_chunks
        definition = {'fields': [
            {'type': 'vector', 'path': 'embedding',
             'numDimensions': settings.embedding_dimensions, 'similarity': 'cosine'},
            {'type': 'filter', 'path': 'patient_id'},
            {'type': 'filter', 'path': 'document_type'},
            {'type': 'filter', 'path': 'document_id'},
        ]}

        async def selected_index():
            cursor = await collection.list_search_indexes()
            indexes = await cursor.to_list(None)
            return next((i for i in indexes if i.get('name') == settings.vector_index_name), None)

        existing = await selected_index()
        if existing is not None:
            stored = existing.get('latestDefinition') or existing.get('definition') or {}
            fields = stored.get('fields', [])
            vector = next((f for f in fields if f.get('type') == 'vector'
                           and f.get('path') == 'embedding'), None)
            filters = {f.get('path') for f in fields if f.get('type') == 'filter'}
            if (not vector or vector.get('numDimensions') != settings.embedding_dimensions
                    or vector.get('similarity') != 'cosine'
                    or not {'patient_id', 'document_type', 'document_id'} <= filters):
                print('ERROR: Existing vector index is incompatible. Nothing was replaced.')
                print('Choose a new VECTOR_INDEX_NAME in .env. Re-upload records if the embedding model changed.')
                return 1
            print('Existing vector index definition verified.')
        else:
            await collection.create_search_index(SearchIndexModel(
                definition=definition, name=settings.vector_index_name, type='vectorSearch'))
            print('Atlas vector index creation requested.')

        deadline = time.monotonic() + wait_seconds
        while True:
            index = await selected_index()
            if index is not None and index.get('status') == 'FAILED':
                print('ERROR: Atlas reports a failed vector index. Inspect the index in Atlas.')
                return 1
            if index is not None and index.get('queryable') is True:
                print('SUCCESS: Vector index is queryable. MongoDB setup is complete.')
                return 0
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print('PENDING: Index creation was requested but the index is not queryable yet.')
                print('Wait in Atlas or rerun this script. Do not test vector retrieval until it is queryable.')
                return 2
            print('Waiting for Atlas to make the index queryable...')
            await asyncio.sleep(min(10, remaining))
    finally:
        await database.close()


def run():
    try:
        return asyncio.run(setup(int(sys.argv[1])))
    except ModuleNotFoundError:
        print('ERROR: Required backend packages are missing. Install backend dependencies from README.md.')
    except Exception as error:
        # Driver messages may contain credentials or record values. Never print them.
        code = getattr(error, 'code', None)
        if code in ('DATABASE_UNAVAILABLE', 'DATABASE_CONFIGURATION'):
            print('ERROR: Database connection failed. Check URI/password, Atlas IP access, and network connectivity.')
        elif code == 11000:
            print('ERROR: Duplicate existing email values prevent creation of the unique email index.')
        elif code == 13:
            print('ERROR: Database user lacks permission for the requested operation.')
        else:
            print('ERROR:', type(error).__name__)
            print('Check .env configuration and Atlas index permissions. No indexes were automatically replaced.')
    return 1


if __name__ == '__main__':
    sys.exit(run())
'@

Push-Location -LiteralPath $BackendPath
try {
    $mongoCode | & $pythonPath - $WaitSeconds
    $setupExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $setupExitCode
