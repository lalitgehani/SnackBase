"""Permission resolution service.

Resolves user permissions by evaluating rules against context data.
Supports role-based and user-specific permissions with OR logic.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.macros.engine import MacroExecutionEngine
from snackbase.core.rules.evaluator import Evaluator
from snackbase.core.rules.parser import Parser
from snackbase.domain.entities.permission import OperationRule
from snackbase.infrastructure.persistence.repositories.permission_repository import (
    PermissionRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class PermissionResult:
    """Result of permission resolution.
    
    Attributes:
        allowed: Whether access is granted.
        fields: List of allowed fields or "*" for all fields.
    """
    
    allowed: bool
    fields: list[str] | str = "*"


class PermissionResolver:
    """Resolves permissions for users based on roles and rules.
    
    Resolution order:
    1. User-specific rules (where user.id matches in rule)
    2. Role-based rules
    3. Wildcard collection rules (*)
    
    Multiple permissions for the same collection are combined with OR logic.
    Deny by default - no matching permissions = access denied.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize the resolver.
        
        Args:
            session: Database session for querying permissions.
        """
        self.session = session
        self.permission_repo = PermissionRepository(session)
        self.macro_engine = MacroExecutionEngine(session)
    
    async def resolve_permission(
        self,
        user_id: str,
        role_id: int,
        collection: str,
        operation: str,
        context: dict[str, Any],
    ) -> PermissionResult:
        """Resolve permission for a user on a collection operation.
        
        Args:
            user_id: User ID for user-specific rules.
            role_id: User's role ID.
            collection: Collection name.
            operation: Operation type (create, read, update, delete).
            context: Evaluation context (user, record, account data).
            
        Returns:
            PermissionResult indicating if access is allowed and which fields.
        """
        logger.debug(
            f"Resolving permission: user_id={user_id}, role_id={role_id}, "
            f"collection={collection}, operation={operation}"
        )
        
        # 1. Get all permissions for this role
        role_permissions = await self.permission_repo.get_by_role_id(role_id)
        
        # 2. Filter permissions for this collection (including wildcard)
        relevant_permissions = [
            p for p in role_permissions
            if p.collection == collection or p.collection == "*"
        ]
        
        if not relevant_permissions:
            logger.debug(f"No permissions found for role_id={role_id}, collection={collection}")
            return PermissionResult(allowed=False, fields=[])
        
        logger.debug(f"Found {len(relevant_permissions)} relevant permissions")
        
        # 3. Evaluate each permission's rule for this operation
        allowed_fields: list[str] = []
        has_wildcard = False
        
        for permission in relevant_permissions:
            # Get the operation rule
            operation_rule = self._get_operation_rule(permission, operation)
            if operation_rule is None:
                continue
            
            # Evaluate the rule
            try:
                rule_allowed = await self._evaluate_rule(
                    operation_rule.rule, context, user_id
                )
                
                if rule_allowed:
                    logger.debug(
                        f"Permission {permission.id} granted access "
                        f"(collection={permission.collection}, rule={operation_rule.rule})"
                    )
                    
                    # Merge fields
                    if operation_rule.fields == "*":
                        has_wildcard = True
                    elif isinstance(operation_rule.fields, list):
                        allowed_fields.extend(operation_rule.fields)
                else:
                    logger.debug(
                        f"Permission {permission.id} denied access "
                        f"(collection={permission.collection}, rule={operation_rule.rule})"
                    )
            except Exception as e:
                logger.error(
                    f"Error evaluating permission {permission.id}: {e}",
                    exc_info=True
                )
                # Deny by default on error
                continue
        
        # 4. Determine final result
        if has_wildcard:
            logger.debug("Access granted with wildcard fields (*)")
            return PermissionResult(allowed=True, fields="*")
        
        if allowed_fields:
            # Remove duplicates while preserving order
            unique_fields = list(dict.fromkeys(allowed_fields))
            logger.debug(f"Access granted with fields: {unique_fields}")
            return PermissionResult(allowed=True, fields=unique_fields)
        
        logger.debug("Access denied - no rules granted access")
        return PermissionResult(allowed=False, fields=[])
    
    def _get_operation_rule(self, permission: Any, operation: str) -> OperationRule | None:
        """Extract operation rule from permission.
        
        Args:
            permission: Permission model.
            operation: Operation type.
            
        Returns:
            OperationRule if exists for this operation, None otherwise.
        """
        import json
        
        try:
            rules_dict = json.loads(permission.rules)
            operation_data = rules_dict.get(operation)
            
            if operation_data is None:
                return None
            
            return OperationRule(
                rule=operation_data.get("rule", "false"),
                fields=operation_data.get("fields", "*")
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.error(f"Invalid rules format for permission {permission.id}")
            return None
    
    async def _evaluate_rule(
        self, rule_expr: str, context: dict[str, Any], user_id: str
    ) -> bool:
        """Evaluate a rule expression.
        
        Args:
            rule_expr: Rule expression string.
            context: Evaluation context.
            user_id: User ID for user-specific rule detection.
            
        Returns:
            True if rule evaluates to true, False otherwise.
        """
        # Check for user-specific rules (contains user.id == "specific_id")
        # This is a simple heuristic - the actual evaluation will determine the result
        is_user_specific = f'user.id == "{user_id}"' in rule_expr or f"user.id == '{user_id}'" in rule_expr
        
        if is_user_specific:
            logger.debug(f"Detected user-specific rule: {rule_expr}")
        
        try:
            # Create lexer and parser for this rule
            from snackbase.core.rules.lexer import Lexer
            lexer = Lexer(rule_expr)
            parser = Parser(lexer)
            
            # Parse the rule
            ast = parser.parse()
            
            # Evaluate with context
            evaluator = Evaluator(context, self.macro_engine)
            result = await evaluator.evaluate(ast)
            
            return bool(result)
        except Exception as e:
            logger.error(f"Error evaluating rule '{rule_expr}': {e}", exc_info=True)
            # Deny by default on error
            return False
