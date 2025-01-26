import requests
import json
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler for errors
error_handler = logging.FileHandler('wordpress_errors.log')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# File handler for debug info
debug_handler = logging.FileHandler('wordpress_debug.log')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)

logger.addHandler(error_handler)
logger.addHandler(debug_handler)

class WordPressError(Exception):
    """Custom exception for WordPress API errors"""
    pass

class WordPressAPIClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, password)
        self.api_base = f"{self.base_url}/wp-json/wp/v2"
        
    def _handle_response(self, response: requests.Response, operation: str) -> Dict:
        """Handle API response and log details"""
        try:
            response_data = response.json()
            if not 200 <= response.status_code < 300:
                error_details = {
                    'status_code': response.status_code,
                    'operation': operation,
                    'url': response.url,
                    'response': response_data,
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(f"API Error: {json.dumps(error_details, indent=2)}")
                self._save_error_log(error_details)
                raise WordPressError(f"API Error: {response_data.get('message', 'Unknown error')}")
            return response_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode response: {str(e)}")
            raise WordPressError(f"Invalid JSON response: {str(e)}")

    def _save_error_log(self, error_details: Dict):
        """Save detailed error information to file"""
        try:
            log_dir = Path("wordpress_logs")
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"error_{timestamp}.json"
            
            with open(log_file, 'w') as f:
                json.dump(error_details, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error log: {str(e)}")


    def convert_date_format(self,date_string):
        try:
            dt = datetime.strptime(date_string, '%Y-%m-%d')
        except ValueError:
            try:
                dt = datetime.strptime(date_string, '%Y%m%d%H%M%S')
            except ValueError:
                dt = datetime.strptime(date_string, '%Y%m%d')
                dt = dt.replace(hour=8, minute=5, second=0)
        
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    def create_post(self,postdate:str, title: str, content: str, image_path: Optional[str] = None,
                   tags: Optional[List[str]] = None, categories: Optional[List[str]] = None,
                   status: str = 'publish') -> Dict[str, Any]:
        logger.info(f"Creating post: {title}")
        try:
            # Handle media upload
            featured_media_id = None
            if image_path:
                logger.debug(f"Uploading media from {image_path}")
                featured_media_id = self.upload_media(image_path)
                if not featured_media_id:
                    logger.warning("Failed to upload featured image")

            # Handle tags
            tag_ids = []
            if tags:
                logger.debug(f"Processing tags: {tags}")
                for tag in tags:
                    tag_id = self.create_tag(tag)
                    if tag_id:
                        tag_ids.append(tag_id)
                    else:
                        logger.warning(f"Failed to create/get tag: {tag}")

            # Handle categories
            category_ids = []
            if categories:
                logger.debug(f"Processing categories: {categories}")
                for category in categories:
                    cat_id = self.create_category(category)
                    if cat_id:
                        category_ids.append(cat_id)
                    else:
                        logger.warning(f"Failed to create/get category: {category}")

            post_data = {
                'title': title,
                'content': content,
                'status': status,
                'post_date': postdate,
                'date': self.convert_date_format(postdate),
                

            }

            if featured_media_id:
                post_data['featured_media'] = featured_media_id
            if tag_ids:
                post_data['tags'] = tag_ids
            if category_ids:
                post_data['categories'] = category_ids

            logger.debug(f"Sending post data: {json.dumps(post_data, indent=2)}")
            response = requests.post(f"{self.api_base}/posts", auth=self.auth, json=post_data)
            print("POST RESPONSE")
            print( response.json())
            #return self._handle_response(response, "create_post")
            post_data['post_id'] = response.json().get('id') if response.status_code == 201 else None
            return post_data

        except Exception as e:
            error_details = {
                'operation': 'create_post',
                'title': title,
                'tags': tags,
                'categories': categories,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            logger.error(f"Failed to create post: {json.dumps(error_details, indent=2)}")
            self._save_error_log(error_details)
            raise WordPressError(f"Failed to create post: {str(e)}")

    def create_tag(self, name: str, description: Optional[str] = None) -> Optional[int]:
        logger.debug(f"Creating/getting tag: {name}")
        try:
            # First try to find existing tag
            existing_tags = requests.get(
                f"{self.api_base}/tags",
                auth=self.auth,
                params={'search': name, 'per_page': 100}
            )
            
            response_data = self._handle_response(existing_tags, "get_tags")
            
            # Check for exact name match (case-insensitive)
            for tag in response_data:
                if tag['name'].lower() == name.lower():
                    logger.debug(f"Found existing tag: {name} (ID: {tag['id']})")
                    return tag['id']

            # Create new tag if not found
            logger.debug(f"Creating new tag: {name}")
            data = {'name': name}
            if description:
                data['description'] = description
                
            response = requests.post(f"{self.api_base}/tags", auth=self.auth, json=data)
            result = self._handle_response(response, "create_tag")
            return result.get('id')

        except Exception as e:
            error_details = {
                'operation': 'create_tag',
                'name': name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            logger.error(f"Failed to create tag: {json.dumps(error_details, indent=2)}")
            self._save_error_log(error_details)
            return None

    def create_category(self, name: str, description: Optional[str] = None,
                       parent: Optional[int] = None) -> Optional[int]:
        logger.debug(f"Creating/getting category: {name}")
        try:
            # First try to find existing category
            existing_categories = requests.get(
                f"{self.api_base}/categories",
                auth=self.auth,
                params={'search': name, 'per_page': 100}
            )
            
            response_data = self._handle_response(existing_categories, "get_categories")
            
            # Check for exact name match (case-insensitive)
            for category in response_data:
                if category['name'].lower() == name.lower():
                    logger.debug(f"Found existing category: {name} (ID: {category['id']})")
                    return category['id']

            # Create new category if not found
            logger.debug(f"Creating new category: {name}")
            data = {'name': name}
            if description:
                data['description'] = description
            if parent:
                data['parent'] = parent

            response = requests.post(f"{self.api_base}/categories", auth=self.auth, json=data)
            result = self._handle_response(response, "create_category")
            return result.get('id')

        except Exception as e:
            error_details = {
                'operation': 'create_category',
                'name': name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            logger.error(f"Failed to create category: {json.dumps(error_details, indent=2)}")
            self._save_error_log(error_details)
            return None

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.api_base}/posts/{post_id}", auth=self.auth)
            return self._handle_response(response, "get_post")
        except Exception as e:
            logger.error(f"Failed to get post {post_id}: {str(e)}")
            return None

    def get_posts(self, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        try:
            response = requests.get(f"{self.api_base}/posts", auth=self.auth, params=params)
            return self._handle_response(response, "get_posts")
        except Exception as e:
            logger.error(f"Failed to get posts with params {params}: {str(e)}")
            return None

    def update_post(self, post_id: int, data: Dict[str, Any]) -> bool:
        try:
            response = requests.put(f"{self.api_base}/posts/{post_id}", auth=self.auth, json=data)
            self._handle_response(response, "update_post")
            return True
        except Exception as e:
            logger.error(f"Failed to update post {post_id}: {str(e)}")
            return False

    def delete_post(self, post_id: int, force: bool = False) -> bool:
        try:
            params = {'force': force}
            response = requests.delete(f"{self.api_base}/posts/{post_id}", auth=self.auth, params=params)
            self._handle_response(response, "delete_post")
            return True
        except Exception as e:
            logger.error(f"Failed to delete post {post_id}: {str(e)}")
            return False

    def upload_media(self, file_path: str, title: Optional[str] = None) -> Optional[int]:
        try:
            if not Path(file_path).exists():
                logger.error(f"Media file not found: {file_path}")
                return None

            with open(file_path, 'rb') as file:
                files = {'file': file}
                data = {'title': title} if title else {}
                response = requests.post(f"{self.api_base}/media", auth=self.auth, files=files, data=data)
                result = self._handle_response(response, "upload_media")
                return result.get('id')
        except Exception as e:
            logger.error(f"Failed to upload media {file_path}: {str(e)}")
            return None

    def get_media(self, media_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.api_base}/media/{media_id}", auth=self.auth)
            return self._handle_response(response, "get_media")
        except Exception as e:
            logger.error(f"Failed to get media {media_id}: {str(e)}")
            return None

    def get_all_media(self, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        try:
            response = requests.get(f"{self.api_base}/media", auth=self.auth, params=params)
            return self._handle_response(response, "get_all_media")
        except Exception as e:
            logger.error(f"Failed to get media list with params {params}: {str(e)}")
            return None

    def update_media(self, media_id: int, data: Dict[str, Any]) -> bool:
        try:
            response = requests.post(f"{self.api_base}/media/{media_id}", auth=self.auth, json=data)
            self._handle_response(response, "update_media")
            return True
        except Exception as e:
            logger.error(f"Failed to update media {media_id}: {str(e)}")
            return False

    def delete_media(self, media_id: int, force: bool = False) -> bool:
        try:
            params = {'force': force}
            response = requests.delete(f"{self.api_base}/media/{media_id}", auth=self.auth, params=params)
            self._handle_response(response, "delete_media")
            return True
        except Exception as e:
            logger.error(f"Failed to delete media {media_id}: {str(e)}")
            return False

    def create_tags(self, tag_names: List[str]) -> List[int]:
        tag_ids = []
        for name in tag_names:
            try:
                tag_id = self.create_tag(name)
                if tag_id:
                    tag_ids.append(tag_id)
                else:
                    logger.warning(f"Failed to create tag: {name}")
            except Exception as e:
                logger.error(f"Error creating tag {name}: {str(e)}")
        return tag_ids

    def get_tag(self, tag_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.api_base}/tags/{tag_id}", auth=self.auth)
            return self._handle_response(response, "get_tag")
        except Exception as e:
            logger.error(f"Failed to get tag {tag_id}: {str(e)}")
            return None

    def get_tags(self, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        try:
            response = requests.get(f"{self.api_base}/tags", auth=self.auth, params=params)
            return self._handle_response(response, "get_tags")
        except Exception as e:
            logger.error(f"Failed to get tags with params {params}: {str(e)}")
            return None

    def update_tag(self, tag_id: int, data: Dict[str, Any]) -> bool:
        try:
            response = requests.put(f"{self.api_base}/tags/{tag_id}", auth=self.auth, json=data)
            self._handle_response(response, "update_tag")
            return True
        except Exception as e:
            logger.error(f"Failed to update tag {tag_id}: {str(e)}")
            return False

    def delete_tag(self, tag_id: int, force: bool = False) -> bool:
        try:
            params = {'force': force}
            response = requests.delete(f"{self.api_base}/tags/{tag_id}", auth=self.auth, params=params)
            self._handle_response(response, "delete_tag")
            return True
        except Exception as e:
            logger.error(f"Failed to delete tag {tag_id}: {str(e)}")
            return False

    def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.api_base}/categories/{category_id}", auth=self.auth)
            return self._handle_response(response, "get_category")
        except Exception as e:
            logger.error(f"Failed to get category {category_id}: {str(e)}")
            return None

    def get_categories(self, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        try:
            response = requests.get(f"{self.api_base}/categories", auth=self.auth, params=params)
            return self._handle_response(response, "get_categories")
        except Exception as e:
            logger.error(f"Failed to get categories with params {params}: {str(e)}")
            return None

    def update_category(self, category_id: int, data: Dict[str, Any]) -> bool:
        try:
            response = requests.put(f"{self.api_base}/categories/{category_id}", auth=self.auth, json=data)
            self._handle_response(response, "update_category")
            return True
        except Exception as e:
            logger.error(f"Failed to update category {category_id}: {str(e)}")
            return False

    def delete_category(self, category_id: int, force: bool = False) -> bool:
        try:
            params = {'force': force}
            response = requests.delete(f"{self.api_base}/categories/{category_id}", auth=self.auth, params=params)
            self._handle_response(response, "delete_category")
            return True
        except Exception as e:
            logger.error(f"Failed to delete category {category_id}: {str(e)}")
            return False